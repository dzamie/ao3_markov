import AO3 as ao3
import re
import random as rand
import json
import sys, argparse

default_length = 100

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--fic', help="AO3 fanfic ID")
parser.add_argument('-I', '--Import', help="import file filename")
parser.add_argument('-E', '--Export', help="export file filename")
parser.add_argument('-l', '--length', help="Markov chain length")
parser.add_argument('-o', '--output', help="Markov chain export filename")
parser.add_argument('-w', '--width',  help="output max line length")
parser.add_argument('-v', '--verbose', action="store_true")
args = parser.parse_args()

# target: make a markov generator from a provided fanfic
# ignore punctuation? start with yes, basic stripping away
# if time later, add option for punct to count as words
# note - chr(8) is a backspace

# markov structure:
# dict of word -> word_prob_cloud
# word_prob_cloud:
# word -> int (frequency)

# storage (stretch goal):
# "word \n prob_cloud \n" repeat
# prob_cloud: "word freq " repeat

##################
## MARKOV STUFF ##
##################

### sanitize
#  input: raw text
# output: regulated text
# turns "fancy" quotes and commas into regular ones
def sanitize(text):
  out = ""
  for char in text:
    if ord(char) > 0x2017 and ord(char) < 0x201C: # fancy '
      out += "'"
    elif ord(char) > 0x201B and ord(char) < 0x2020: # fancy "
      out += '"'
    else:
      out += char
  return out

### prettify
#  input: text probably from a markov
# output: text without the spaces before some punctuation
def prettify(text):
  return re.sub(r' ([.!?:,-/;])', r'\1', text)

### pretty_cmd
#  input: text probably from a markov
# output: prettified text, sized to avoid line breaks in a cmd window
def pretty_cmd(text, length = 80):
  out = ""
  text = prettify(text).split(' ')
  line = 0
  for word in text:
    if line + len(word) + 1 > length:
      out += '\n'
      line = 0
    out += word + " "
    line += len(word) + 1
  return out
  

### copy_prob
#  input: 1 dict of type str->int
# output: 1 dict of type str->int
# performs a deep copy, so actions on input or output have no effect on the other
def copy_prob(prob):
  out = {}
  for key in prob.keys():
    out[key] = prob[key]
  return out

### copy_markov
#  input: 1 markov
# output: 1 identical markov
# deep copy thing for markovs
def copy_markov(markov):
  out = {}
  for key in markov.keys():
    out[key] = copy_prob(markov[key])
  return out

### merge_probs
#  input: 2 dicts of type str->int
# output: 1 dict  of type str->int
# for common keys: add values, store
# for unique keys: store
def merge_probs(prob1, prob2):
  out = {}
  for key in prob1.keys():
    if key in prob2:
      out[key] = prob1[key] + prob2[key]
    else:
      out[key] = prob1[key]
  for key in prob2.keys():
    if not (key in prob1):
      # (prob1 AND prob2) already covered in previous loop
      out[key] = prob2[key]
  return out

### merge_markovs
#  input: 2 dicts of type str->(str->int)
# output: 1 dict  of type str->(str->int)
# pretty much like merge_probs but for full markovs
def merge_markovs(mark1, mark2):
  out = {}
  for key in mark1.keys():
    if key in mark2:
      out[key] = merge_probs(mark1[key], mark2[key])
    else:
      out[key] = copy_prob(mark1[key])
  for key in mark2.keys():
    if not(key in mark1):
      # again, this has already been handled
      out[key] = copy_prob(mark2[key])
  return out

### add_pair
#  input: 1 dict of type str->(str->int), 2 strings
# output: 1 dict of type str->(str->int)
# adds a word-pair to the given markov, then returns it, modified
def add_pair(markov, word1, word2):
  if word1 in markov: # if the first word is an established first-word
    if word2 in markov[word1]: # if the second word has already followed the first
      markov[word1][word2] += 1
    else:
      markov[word1][word2] = 1
  else:
    markov[word1] = {}
    markov[word1][word2] = 1
  return markov # superfluous, since markov is mutable

### add_string
#  input: 1 dict of type str->(str->int), 1 string
# output: 1 dict of type str->(str->int)
# takes a string of space-separated words and adds them all to a markov
def add_string(markov, input):
  list = input.split(' ')
  for i in range(0, len(list) - 1):
    add_pair(markov, list[i], list[i + 1])
  return markov

### parse_string
#  input: 1 string, 1 boolean optional
# output: 1 string
# takes a string of natural text, returns a string of space-separated words
# plan to add incl_punct as a flag to include non A1 "words"
def parse_string(input, incl_punct = False):
  out = input.lower()
  out = sanitize(out) # get rid of the "weird quotes" from 0x20XX
  if incl_punct:
    out = re.sub(r'(\W)', r' \1 ', out) # what could go wrong?
    out = re.sub(r" ' ", r"'", out) # split contractions suck
    # print("whoops!")
  else:
    out = re.sub("[-']",'',out) # hyphenated and contractions count as words
    out = re.sub('[^\w\s]', ' ', out) # strip all nonwords, replace with space
  out = re.sub('\s+', ' ', out) # strip repeated spaces
  return out

### sum_starts
#  input: a markov dict
# output: a frequency dict of starting words
# helps speed up markov making
def sum_starts(markov):
  out = {}
  for key in markov.keys():
    count = 0
    for key2 in markov[key].keys():
      count += markov[key][key2]
    out[key] = count
  return out

### step
#  input: markov dict, starting word
# output: next word
# simplest step of a markov. if no following word is found, jumps to a random one that is
def step(markov, sums, input):
  if input in markov.keys():
    # choose a random part of the "dartboard" of each word
    num = rand.randint(0, sums[input])
    for key in markov[input]:
      # climb up the "dartboard"
      num -= markov[input][key]
      if num < 1: # at 0 or less, that's where it's landed
        return key
  else:
    return list(markov.keys())[rand.randint(0, len(markov.keys())-1)]

### walk
#  input: a markov, an int
# output: a %length%-words long number of steps
# a walk is a bunch of steps, one after the other.
def walk(markov, length):
  out = ""
  sums = sum_starts(markov)
  curr = list(markov.keys())[rand.randint(0, len(markov.keys())-1)]
  for i in range(0, length):
    out += curr + " "
    curr = step(markov, sums, curr)
  return out # let's see if this works

### markov
#  input: raw text input
# output: full markov
# just to make things easier
def markov(raw_input):
  return add_string({}, parse_string(raw_input, True))

def export_markov(markov, name = "save.txt"):
  with open(name, 'w') as f:
    f.write(json.dumps(markov))

def import_markov(name = "save.txt"):
  with open(name, 'r') as f:
    out = json.loads(f.read())
    for one in out.keys():
      for two in out[one].keys():
        out[one][two] = int(out[one][two])
    return out

###############
## AO3 STUFF ##
###############

### load_fic
#  input: int fic ID, boolean verbose optional
# output: Work object with loaded chapters
# will fail with normal error if invalid id given - should fix later
def load_fic(id, verbose = False):
  if verbose:
    print("Loading fic information...")
  out = ao3.Work(id)
  if verbose:
    print("Gathering chapter list...")
  out.load_chapters()
  if verbose:
    print("Table of Contents gathered!")
  return out

### load_chapters
#  input: Work, array of chapter # ints optional, boolean verbose optional
# output: array of chapter texts
# if left empty, will summon all chapter texts
def load_chapters(fic, ch_arr = [], verbose = False):
  out = []
  if ch_arr == []:
    ch_arr = range(1, fic.chapters + 1)
  for ch in ch_arr:
    if verbose:
      print("Loading chapter " + str(ch) + "...")
    out.append(fic.get_chapter_text(ch))
  if verbose:
    print("All chapters loaded!")
  return out

################
## BOTH STUFF ##
################

### fic_markov
#  input: int fic id, array of chapter # ints optional, boolean verbose optional
def fic_markov(id, ch_arr = [], verbose = False):
  out = {}
  add = {}
  fic = load_fic(id, verbose = verbose)
  text = load_chapters(fic, verbose = verbose)
  for chapter in text:
    add = markov(chapter)
    out = merge_markovs(add, out)
  return out

def main():
  mark = {}
  if args.fic:
    mark = fic_markov(int(args.fic), verbose = args.verbose)
  elif args.Import:
    mark = import_markov(str(args.Import))
  else:
    print("Error: no input given. Exiting...")
    exit(2)
  # we now have a markov
  
  if args.Export:
    export_markov(mark, str(args.Export))
  
  text = walk(mark, int(args.length) if args.length else default_length)
  text = pretty_cmd(text, int(args.width)) if args.width else prettify(text)
  
  if args.output:
    with open(str(args.output), 'w') as f:
      f.write(text)
  else:
    print(text)

if __name__ == "__main__":
  main()