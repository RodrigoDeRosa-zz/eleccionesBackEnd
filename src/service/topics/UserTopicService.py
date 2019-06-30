import datetime

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfTransformer

from src.db.dao.UserHashtagDAO import UserHashtagDAO


class UserTopicService:

    @classmethod
    def calculate_users_topics_matrix(cls):
        """ This method calculate the user-topic matrix. """

        # TODO preguntarle a rodri:
        # Se puede hacer algo parecido a lo que se hizo en  UserHashtagDAO() ??
        # Tener en memoria un dict { topico: [hashtags] } ???
        # Que dimensiones tiene eso?

        # TODO Pedir los topicos que se crearon
        # This topics will be the collumns of the matrix
        topics_col = sorted([])
        hashtags_quantity = len(topics_col)

        # Initialice row's vector matrix and data vector
        users_row = []
        data = []

        # Retrieve yesterday's hashtags gruped by user
        hashtags_by_users = UserHashtagDAO().get_hashtags_aggregated_by_user()
        for user_with_hashtags in hashtags_by_users:
            user = user_with_hashtags['_id']
            hashtags = user_with_hashtags['hashtags_array']

            user_hashtags_vector = [0] * hashtags_quantity
            # for hashtag in hashtags:
            # Pedir  a que topico pertenece el hashtag
            # sumar uno en esa posicion del vector resultado

            if sum(user_hashtags_vector) > 0:
                # guardar el vector en la matriz
                users_row.append(user)
                data.append(user_hashtags_vector)

        cls.create_matrix_and_save(data)

    @classmethod
    def create_matrix_and_save(cls, data):
        """ Method which receive vector data and create a csr matrix.
        After that apply TF-IDF and save it."""
        # Create np array to be used in the matrix
        np_data = np.array(data)
        matrix = csr_matrix(np_data)

        # Apply TF-IDF
        tfidf_transformer = TfidfTransformer()
        tf_idf_matrix = tfidf_transformer.fit_transform(matrix)

        date = datetime.datetime.today()
        csr_matrix.save_npz(f'{str(date.year)}-{str(date.month)}-{str(date.day)}', tf_idf_matrix)
