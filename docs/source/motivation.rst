Motivation
==========

To deal with experimental and simulation data is very often a pain due to an non existing standard data format.

Every lab, and even worse, every staff uses different data formats to store the measured data during an experimental study.
Sometimes the raw data ist given by means of undocumented csv files, sometimes a bunch of Excel files with some strange
tables layouts are available from the labs. This results often in an uncomplete data set.

To predict a system behavior the nessecary simluation task depend on these experimental result inorder to calibrate the simulation models.
Very often the link to the raw experimental data is broken by using only some key result from the experiments.

The aim of this project is to fill the gap by providing an open self describing data structure to store results from
experiments and simulations in the same manner.

It should be easy to define a standard data format for a particular experimental test setup based on the `sdata` environment within a specific project.
Furthermore the data should be readable in future.

