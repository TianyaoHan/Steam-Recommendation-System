# Design of Personalized Steam Video Game Recommendation System

<br>

## 1. Statement of Work

<br>

Nowadays, online stores provide us the ever-growing number and variety of items to which we have access. But, the famous [Jame Experiment](https://www.ncbi.nlm.nih.gov/pubmed/11138768)[1] shows that a lot choices does seem appealing, but this option overload may in fact paralyze us. Thus, while building a database system to fulfill customers’ needs, a personalized recommendation system that provides narrowing down choices, but still providing plenty of possibilities would make customers more satisfied.

<br>

In this database project, we used steam video game and bundle datasets for our application. The brief is to create a video game and bundle database system for recommendation, meaning as well as build up a database that allows users to find and select games, the application should also generate personalized narrow down game-list and bundle-list for users to explore. The basic goal of the project is to provide detailed information of games in different categories and to understand relationships between users and games, games and bundles, and users and bundles. The main challenging task is to parse the semantics that describe relationships between sets of items, to build up relationship between games and bundles, to determine what features (including genres, developer, price, etc.) make games attractive to a user, and to determine personalized ranking in order of importance.

<br>

The organization of the project is to: 

  - Analyze relationships between users and the games they played using Entity Relationship diagram to establish structural metadata and generate the database.
  - Implement recommendation algorithms such as Content-based, Collaborative Filtering to come up with a personalized ranking in order of importance to a user.
  - Build a front-end website application to allow users to find games and also generate personalized narrow down game-list for users to explore.

<br>

## 2. Methodology and Implementation Plan

<br>

### 2.1	Datasets

<br>

To do so, we used six steam video game and bundle datasets. Five datasets are from the [​University of California San Diego-Julian McAuley’ s Recommender Systems](http://cseweb.ucsd.edu/~jmcauley/datasets.html#steam_data)
[2,3,4]​ Datasets-Steam Video Game and Bundle Data​ :

Australian User Reviews dataset: comprises 25799 reviews.

- Australian User Items dataset: consists of 32134 games.

- Steam Games dataset : comprises 376 tags.

- Steam Reviews dataset: consists of 23818 users.

- Bundle dataset: contains 496 bundles.

and another one is from ​[Kaggle’s Steam games complete dataset​](https://www.kaggle.com/trolukovich/steam-games-complete-dataset): contains more than 40833 games.


These datasets provide detailed information as regards user/game interactions such as what games users played and how long, whether they recommended as well as bundle items, promotions, and what bundles were purchased by each user. The combination of the six datasets will enable us to build a database system that provides users access to thousands of games and the parsed semantic relationships between user and games will allow us to assess the extent to which items that are desirable to a user.

### 2.2 Entity-Relationship Diagram

<br>

![Figure 1. Entity Relationship Diagram for Steam Video Games and Bundles](https://github.com/TianyaoHan/Steam-Recommendation-System/blob/master/4111DB_proj_v2.jpeg "ER Diagram")

We firstly used Entity Relational Model to build a relational database. The general entity set includes game, user, review, bundle, publisher, developer, genre, language, spec. We then went through the normalization process to come up with a collection of tables.

### 2.3 SQL Schema

<br>

CREATE TABLE users(
user_id VARCHAR(50) PRIMARY KEY,
playtime_total_forever NUMERIC(10,0),
playtime_total_2week NUMERIC(10,0));

<br>

CREATE TABLE games(
game_id VARCHAR(15) PRIMARY KEY,
price NUMERIC(5,2) NOT NULL,
early_access BOOLEAN,
achievements NUMERIC(2,0),
app_name VARCHAR(50) NOT NULL, 
discount_price NUMERIC(5,2) NOT NULL,
release_date DATE,
recent_reviews NUMERIC(5,0),
recent_rating NUMERIC(3,1),
all_reviews NUMERIC(10,0),
all_rating NUMERIC(3,0),
UNIQUE(app_name),
CHECK (price > discount_price AND discount_price>=0));

<br>
 
CREATE TABLE play (
user_id VARCHAR(50) REFERENCES users ON DELETE CASCADE,
game_id VARCHAR(15) REFERENCES games ON DELETE CASCADE,
playtime_forever NUMERIC(12,0)NOT NULL,
playtime_2week NUMERIC(12,0) NOT NULL,
PRIMARY KEY(user_id, game_id));

<br> 

CREATE TABLE reviews (
user_id VARCHAR(50),
game_id VARCHAR(15),
funny VARCHAR(50),
posted_time  DATE,
last_edited_time DATE,
help_score NUMERIC(3,2),
help_num INTEGER,
recommend BOOLEAN,
review TEXT);

<br> 

CREATE TABLE bundles (
bundle_id VARCHAR(15) PRIMARY KEY,
bundle_name VARCHAR(100),
bundle_price NUMERIC(6,0),
bundle_final_price NUMERIC(6,0),
bundle_discount NUMERIC(2,2),
CHECK (bundle_price >= bundle_final_price AND bundle_final_price>=0),
CHECK (bundle_discount>=0 AND bundle_discount<=1));

<br>

CREATE TABLE bundle_game (
bundle_id VARCHAR(15),
game_id VARCHAR(15) REFERENCES games ON DELETE CASCADE,
PRIMARY KEY(bundle_id,game_id));

<br>

CREATE TABLE genres(
game_id VARCHAR(15) REFERENCES games ON DELETE CASCADE,
genre_name VARCHAR(50),
PRIMARY KEY(game_id, genre_name));

<br>

CREATE TABLE publishers (
  game_id VARCHAR(15) REFERENCES games ON DELETE CASCADE,
  publisher_name VARCHAR(50),
  PRIMARY KEY(game_id, publisher_name))
;

<br>

CREATE TABLE tags(
  game_id VARCHAR(15) REFERENCES games ON DELETE CASCADE,
  tag_name VARCHAR(50),
  PRIMARY KEY(game_id, tag_name));

<br> 

CREATE TABLE specs(
  game_id VARCHAR(15) REFERENCES games ON DELETE CASCADE,
  spec_name VARCHAR(50),
  PRIMARY KEY(game_id, spec_name)
);

<br>

CREATE TABLE languages(
  game_id VARCHAR(15) REFERENCES games ON DELETE CASCADE,
  language_name VARCHAR(100),
  PRIMARY KEY(game_id, language_name)
);

<br>  

CREATE TABLE developers(
  game_id VARCHAR(15) REFERENCES games ON DELETE CASCADE,
  developer_name VARCHAR(100),
  PRIMARY KEY(game_id, developer_name)
);

<br>

CREATE TRIGGER delete_bundle_id AFTER DELETE ON games
FOR EACH ROW
EXECUTE PROCEDURE process_delete_bundle_id();

<br>

CREATE OR REPLACE FUNCTION process_delete_bundle_id()
  RETURNS trigger AS
$$
BEGIN   
    DELETE FROM bundles
    WHERE bundle_id in (SELECT DISTINCT bundle_id 
                        FROM bundles
                        WHERE game_id = orow.game_id);
    RETURN NULL;
END;

$$ LANGUAGE plpgsql;

<br>


### 2.4 Recommendation Algorithm

<br>

Recommendation algorithm: Collaborative Filtering or/and Content-based Filtering (also known as the personality-based approach). We used a user’s past behavior (games previously purchased, time spent on playing those games, numerical ratings given to those games) as well as similar decisions made by other users to predict games that the user may have an interest in.

It mainly uses three methods to do the recommendation:
  1. find highest weighted mean of game ratings 
  2. do TF-IDF on game overviews and find top games with highest cosine-similarity(content based) 
  3. use Spark ALS algorithm(a kind of collaborative filtering user-user recommendation).

<br>

## 3 Web Front-End

<br>

The general “entities” that are involved are: game, user, play, review, bundle, publisher, developer, etc.
<br>

1. The designed relational database allows users to search and review games, the application should also generate personalized narrow down game-list for users to explore.
2. The database was built on [Google Cloud Platform](https://cloud.google.com/) using [Python](https://www.python.org), [Spark](https://spark.apache.org), [Scikit-learn](https://scikit-learn.org/), [PostgreSQL](https://www.postgresql.org), and [Flask](https://flask.palletsprojects.com/).
3. Weblink:http://35.227.83.90:8111/

<br>

## 4 Object-Relational Features

<br>

%Part 4: We will extend the schema of Part 1 with object-relational features (ongoing).

<br>

## Appendix

<br>

### A1. Software Package Installation

<br>

 - JDK 8: Download .tar.gz and install manually.
 - Spark: Download .tgz and install manually.
 - Postgres: in a remote server provided by professor .

<br>

All packages list below can be installed directly by pip3.

<br>

 - Flask: `$ pip3 install flask` `$ pip3 install flask_login`
 - sqlalchemy: `$ pip3 install sqlalchemy`
 - pandas: `$ pip3 install pandas`
 - sklearn: `$ pip3 install scikit-learn`
 - psycopg2: `$ pip3 install psycopg2`
 - numpy: `$ pip install numpy`

<br>

### A2. Directory

<br>

 - templates: web pages.
 - server.py: flask app.
 - recomAlg.py: recommendation algorithm.

<br>

### A3. Steps to run our application

<br>

- run the application: `$ python server.py`.

<br>

## References

<br>
<a id="1">[1]</a> 
S. S. Iyengar, M. R. Lepper. 
When choice is demotivating: Can one desire too much of a good thing? Journal of Personality and Social Psychology, 79(6), 995–1006, 2000.
<br>
<a id="2">[2]</a> 
Wang-Cheng Kang, Julian McAuley. Self-attentive sequential recommendation. ICDM, 2018.
<br>
<a id="3">[3]</a> 
Meng-ting Wan, Julian McAuley. Item recommendation on monotonic behavior chains. RecSys, 2018.
<br>
<a id="4">[4]</a> 
Apurva Pathak, Kshitiz Gupta, McAule Julian. Generating and personalizing bundle recommendations on Steam. SIGIR, 2017.


