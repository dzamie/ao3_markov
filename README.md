# ao3_markov

Creates Markov chain generators from stories hosted on Archive Of Our Own

## Usage
### As a module
pip installation is not currently supported.
This module uses the [ao3_api](https://github.com/ArmindoFlores/ao3_api) module to create a Markov Chain generator from an AO3 work ID.
```
>>> import ao3_markov
>>>markov = ao3_markov.fic_markov(6413431)
```
You can limit the generator's source to certain chapters with the ```ch_arr``` argument, and watch its progress with the ```verbose``` argument.
```
>>> small_kov = ao3_markov.fic_markov(6413431, ch_arr = [1,2,5,8,9], verbose = True)
Loading fic information...
Gathering chapter list...
Table of Contents gathered!
Loading chapter 1...
Loading chapter 2...
Loading chapter 5...
Loading chapter 8...
Loading chapter 9...
All chapters loaded!
```
The ```walk``` method uses the provided generator to create a Markov Chain, starting from a random word. Returns a string.
```
>>> print(ao3_markov.walk(markov, 20))
harmed! and your new route to traverse carefully lift ghost an area, at everything that. something that
```
Generators can be combined with ```merge_markovs```. This combines frequencies additively, which can be used to influence pair frequencies and to create generators from multiple works.
```
>>> dbl_markov = ao3_markov.merge_markovs(markov, small_kov)
```
Generators can be exported and imported, allowing for offline use.
```
>>> ao3_markov.export_markov(markov, "knight.txt")
>>> mark_2 = ao3_markov.import_markov("knight.txt")
>>> markov == mark_2
True
```
### As a program
```ao3_markov``` can be used from the terminal, with a handful of flags for input, output, length, and verbosity.
```
[user@home]$ python ao3_markov.py -I "knight.txt" -l 20
translate before practically vibrating. this has headed further deterred them. quirrel didn't it will be alright, "
[user@home]$
```
