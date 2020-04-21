# Twitter: Argentinian Elections 2019
## Software Engineering Integral Final Work

This repository holds all the codebase for the Back End server used in the development of the application found in
http://elecciones2019.fi.uba.ar/. 
All this code, as well as all the code you can find [here](https://github.com/RodrigoDeRosa/eleccionesFrontEnd) was 
designed, coded and tested by a team integrated by [Rodrigo De Rosa](https://github.com/RodrigoDeRosa), 
[Facundo Guerrero](https://github.com/facuguerrero) and [Marcos Schapira](https://github.com/marcossch) in the context 
of the Software Engineering integral final work at the University of Buenos Aires. In this readme, the basics of this 
application will be explained as well as how to run it.

## What is this project about?

The point of this whole project was to analyze all the content posted on Twitter related to the Presidential elections
that took place in Argentina in 2019. The main idea was to identify how similar were the conversation topics the
supporters of each political party talked about and, with this, identify how similar each group was to the others.

To be able to make this analysis, it was needed to:

* Find our group of interest; this means whose tweets we would analyze.
* Determine which presidential candidate each of our users of interest supported.
* Get all the hashtags each of this users used.
* Find topics of conversation; this would be communities of nodes in a hashtag co occurrence graph.
* Analyze how common is the use of one or another topic of conversation for one or another support group (or political
party).
* Discover how related are the opinions of the different political parties by comparing how many conversation topics
they have in common.

## What does this application do?

This part of the project is what we called the **Download and Process** application; here, we retrieved all the data we
needed from Twitter, we processed it, and we store the metrics we would later need. Also, here, we created our co
occurrence graphs, we made our similarity comparisons and found our conversation topics. Each of these things was 
done automatically on a daily basis and will be explained in the following sections.

### Data retrieval

To make our analysis, it was necessary to retrieve data from Twitter; more specifically, we needed to get some users
to analyze and discover both which presidential candidate did they support and what did they tweet about. 

To do this, we analyzed every user that followed at least a presidential candidate or their vice president candidate.
During this analysis, we determined who each of these users supported by analyzing who did they follow and who did they
retweet; by pondering these two factors, we created a system to determine if a user supported one or another party with
a certain degree of confidence.

Regarding the users' opinion, we retrieved all the hashtag each of these users used and stored them to create what we
call the *co occurrence graph*; in the following section we will explain what it means.

### Hashtag co occurrence graph

We say that two hashtags co occur when they are used in the same tweet. This means that if we found the following tweet:

```
The #cat is #under the #table:
```

The hashtags `#cat`, `#under` and `#table` co occurred in couples. This is: `(cat, under)`, `(cat, table)` and
`(under, table)` are the three co occurrences found in this tweet.

Our analysis process included storing all co occurrences found in our users of interest's tweets to create a graph. This
graph would have the following characteristics:

* Each node represents a hashtag.
* Each edge joining two nodes represents a co occurrence between the hashtags said nodes represent, where the weight
of said edge is the number of times these hashtags co occurred.
* The graph is non directed.

Thin edges would be removed to make the graph's processing faster, considering also that they would make no difference
in the final result.

Once this graph was ready, we searched for conversation topics.

### Conversation topics

Conversation topics are a fancy, descriptive name for communities in our co occurrence graph. Given that the graph was
a description of how hashtags were used together, finding communities in this graph would mean to find specific 
discussion topics. To do this, we used an algorithm called [OSLOM](http://www.oslom.org/), developed by Andrea 
Lancichinetti, Filippo Radicchi, José Javier Ramasco and Santo Fortunato.

This algorithm would give us all the information we needed about how hashtags clustered themselves, allowing us to
analyze the supporters of which parties talked about which topics of conversation, and how similar they were.

### Similarities

To analyze the similarities between the supporters of each party, we created a system in which we took the hashtags each
of the users used and placed them in each of our clusters (a.k.a. conversation topics); then, we compared the used 
topics of users supporting every party against users supporting every other party (including itself) using matrix 
multiplication and, as a result, we got a value that represented the **similarity**.

To explain this in a more simple way, the similarity index reflects how many topics of conversations the supporters of 
one party share with the supporters of another party; this is, how similar their general speech is.

### User network

The last feature this application has is the analysis of the user network. In this part of the project we tried to
describe how connected were the supporters of one party between each other and with the supporters of others party.

What we did here was, for each party, count the number of other users (in total) the supporters of said party followed
and, from that number, get the proportion of follows that were "outside" of the party the user in question supported.
This allowed us to analyze how polarized our universe of users was because we knew exactly how tight were the connections
between users with the same ideology and how loose between those with different political views.

## Technologies used

This application was developed as a Python [Flask](https://flask.palletsprojects.com/en/1.1.x/) server, with a 
[MongoDB](https://www.mongodb.com/) as a database management service. The decision was made based on the simplicity of 
Flask and the non relational characteristics of our data. Although it was not necessary for this application to be a web
server, it simplified the process of activating a deactivating some features by simply making requests.

To simplify our work, we used some already developed libraries that made our job easier in some aspects. To mention a
few:

* [APScheduler](https://apscheduler.readthedocs.io/en/stable/) was used to start analysis jobs every day, to analyze the
collected data and generate new metrics. This library allowed us to set the time of start for each of our processes, 
which ran periodically.
* [Twython](https://twython.readthedocs.io/en/latest/) allowed us to retrieve all the data we needed from Twitter 
services.
* [numpy](https://numpy.org/), [pandas](https://pandas.pydata.org/), [scipy](https://www.scipy.org/) and 
[sklearn](https://scikit-learn.org/stable/) were all used to handle large data sets and large matrix multiplications, and
mainly used for similarity calculations.
* [mongomock](https://github.com/mongomock/mongomock) allowed us to develop tests where we wanted to simulate the access
to our database.
* [Slack Client](https://slack.dev/python-slackclient/) was used as a communication tool; it let us send messages to 
Slack rooms when certain situations we were particularly interested in presented.

## Deployment

This application was running in a server owned by the University of Buenos Aires and was deployed there using the
`startup` script; there, we injected the database parameters (which were only stored in the server for security) to
connect with an specific user and password. The deployment was made manually via SCP due to university's restrictions.

## How to run the server locally

In order to run the server locally, first make sure you have installed:

* `Python 3.6`
* `mongo` running in the port 27017

Once that is ready, you can start the server by running `make prepare` and `make run` in the project's root.
