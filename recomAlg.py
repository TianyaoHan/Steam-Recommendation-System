#!/usr/bin/env python

import psycopg2
import numpy as np
import pandas as pd

from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

#
import os
import sys
import itertools
from math import sqrt
from operator import add
from os.path import join, isfile, dirname

from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.recommendation import ALS
from pyspark.sql import Row
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("ALSApp").getOrCreate()

# Model 1: Content based
## model
class content_based:
    """
    content based recommendation
    """
    print("Recommendation: Content Based")
    
    def __init__(self, X):
        """
        conn: db engine
        """
        self.data = X

    def get_recommendations(self, name):
        # tfidf
        tf = TfidfVectorizer(analyzer='word', ngram_range=(1, 3), min_df=0, stop_words='english')
        tfidf_matrix = tf.fit_transform(df['feature'].fillna(''))
        # Compute the cosine similarity matrix
        cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
        #Construct a reverse map of indices and movie titles
        indices = pd.Series(self.data.index, index=self.data['app_name']).drop_duplicates()
    
        # Get the index of the movie that matches the title
        idx = indices[name]
        # Get the pairwsie similarity scores of all movies with that movie
        sim_scores = list(enumerate(cosine_sim[idx]))
        # Sort the movies based on the similarity scores
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        # Get the scores of the 10 most similar movies
        sim_scores = sim_scores[1:11]
        # Get the movie indices
        game_indices = [i[0] for i in sim_scores]
        # Return the top 10 most similar movies
        return self.data['app_name'].iloc[game_indices]

## get data
def get_game_data(eng):
    """
    read in game ids, game tags, game languages, game genres
    """
    print("read in game data from database")
    dfin = pd.read_sql_query('''
    SELECT games.game_id, games.app_name, tags.tag_name, genres.genre_name, languages.language_name
    FROM games
    LEFT JOIN tags ON games.game_id = tags.game_id
    LEFT JOIN genres ON games.game_id= genres.game_id
    LEFT JOIN languages ON games.game_id=languages.game_id;
    ''', eng)
    # combine columns to list
    apps = dfin[['game_id','app_name']].drop_duplicates()
    tags = dfin[['game_id','tag_name']].drop_duplicates().groupby('game_id').agg({
            'tag_name':lambda x: list(x)})
    genres = dfin[['game_id','genre_name']].drop_duplicates().groupby('game_id').agg({
            'genre_name':lambda x: list(x)})
    languages = dfin[['game_id','language_name']].drop_duplicates().groupby('game_id').agg({
            'language_name':lambda x: list(x)})
    data = apps.merge(tags, on='game_id').merge(genres, on='game_id').merge(languages, on='game_id')
    data['feature'] = data['tag_name'] + data['genre_name']+ data['language_name']
    
    data['feature'] = data['feature'].map(str).str.lower()
    return data[['game_id', 'app_name', 'feature']].drop_duplicates()


# Model 2: Collaborative Filtering
def get_top_games(engine):
    """
    read top games based on rating
    """
    topgames = pd.read_sql_query('''
    SELECT game_id, app_name
    FROM games
    WHERE all_reviews>10000.0
    ORDER BY all_rating DESC;
    ''', engine)
    return topgames[:10].game_id.tolist()


def get_review_data(eng):
    """
    read in game ids, game tags, game languages, game genres
    """
    print("read in review data from database")
    gameids = pd.read_sql_query('''
    SELECT game_id
    FROM games;
    ''', eng)
    
    userids = pd.read_sql_query('''
    SELECT user_id
    FROM users;
    ''', eng)
    
    reviews = pd.read_sql_query('''
    SELECT *
    FROM reviews
    LEFT JOIN games on reviews.game_id = games.game_id
    LEFT JOIN users on users.user_id = reviews.user_id
    ;
    ''', eng)
    
    # calculate weight ratings
    reviews = reviews.loc[:,~reviews.columns.duplicated()]
    temp = reviews [['funny', 'help_score','help_num', 'recommend','playtime_total_2week','playtime_total_forever']].astype(float)*1.0
    temp_scaled = (temp - np.min(temp))/(np.max(temp)-np.min(temp))
    reviews['rating'] = temp_scaled.sum(axis=1)
    ratings = reviews[['user_id','game_id','rating']]
    ratings_table_in = pd.pivot_table(ratings, index=['user_id'], columns=['game_id'],fill_value=np.nan)
    # create pivot table
    user_id = ratings_table_in.index.get_level_values(0)
    n_users = len(user_id)
    game_id = ratings_table_in.columns.get_level_values(1).astype(int)
    ratings_table = ratings_table_in
    ratings_table.index=np.arange(n_users)
    ratings_table.index.name='user_id'
    
    return user_id, game_id, ratings_table

def unpivot(frame):
    N, K = frame.shape
    data = {'value': frame.to_numpy().ravel('F'),
            'variable': np.asarray(frame.columns.get_level_values(1).astype(int)).repeat(N),
            'date': np.tile(np.asarray(frame.index), K)}
    pdf = pd.DataFrame(data, columns=['date', 'variable', 'value'])
    
    pdf = pdf.rename(columns={'date':'user_id',
                   'variable':'game_id',
                   'value':'rating'})
    return pdf.dropna()


def get_cc_recommendations(data):
    #[userid, gameid, ratings_table] = get_review_data(eng)
    #data = unpivot(ratings_table)
    exec(open(os.path.join(os.environ["SPARK_HOME"], 'python/pyspark/shell.py')).read())
    df_ratings = spark.createDataFrame(data)
    df_ratings.createOrReplaceTempView("ratings")
    (training, test) = df_ratings.randomSplit([0.8, 0.2])
    als = ALS(maxIter=5, regParam=0.01, userCol="user_id", itemCol="game_id", ratingCol="rating", coldStartStrategy="drop")
    model = als.fit(training)
    # Evaluate the model by computing the RMSE on the test data
    # predictions = model.transform(test)
    # evaluator = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")
    # rmse = evaluator.evaluate(predictions)
    # print("Root-mean-square error = " + str(rmse))
    # # Generate top 10 movie recommendations for each user
    userRecs = model.recommendForAllUsers(10)
    #Generate top 10 user recommendations for each movie
    gameRecs = model.recommendForAllItems(10)

    return userRecs.toPandas(), gameRecs.toPandas()
