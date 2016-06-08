#!/usr/bin/env python
from __future__ import print_function
import os
import sys
import json
from datetime import datetime
import tempfile

# 3rd party
import luigi

from pathutils import project_path

PROJECT_CODE_PATH = os.path.join(project_path(), 'code')
sys.path.append(PROJECT_CODE_PATH)

from util.nectar_s3_task import NectarS3Task
from util.nectar_local_task import NectarLocalTask

TheTaskClass = NectarLocalTask if os.getenv('ENV', 'local') == 'local' else NectarS3Task

# Author: Olivier Grisel <olivier.grisel@ensta.org>
#         Lars Buitinck <L.J.Buitinck@uva.nl>
#         Chyi-Kwei Yau <chyikwei.yau@gmail.com>
# License: BSD 3 clause

from time import time

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import NMF, LatentDirichletAllocation
from sklearn.datasets import fetch_20newsgroups

n_samples = 2000
n_features = 1000
n_topics = 10
n_top_words = 20


def get_top_words(model, feature_names, n_top_words):
    top_words = {}
    for topic_idx, topic in enumerate(model.components_):
        top_words[topic_idx] = " ".join([feature_names[i]
                        for i in topic.argsort()[:-n_top_words - 1:-1]])
    return top_words


# Load the 20 newsgroups dataset and vectorize it. We use a few heuristics
# to filter out useless terms early on: the posts are stripped of headers,
# footers and quoted replies, and common English words, words occurring in
# only one document or in at least 95% of the documents are removed.


class VectorizationDataTask(TheTaskClass):
    today = luigi.Parameter(
           default=datetime.strftime(datetime.now(), '%Y-%m-%d')
          ) 

    def requires(self):
        return None

    def run(self):
        print("Loading dataset...")
        t0 = time()
        dataset = fetch_20newsgroups(shuffle=True, random_state=1,
                                     remove=('headers', 'footers', 'quotes'))
        data_samples = dataset.data
        print("done in %0.3fs." % (time() - t0))
        with self.output().open('w') as out_f:
            out_f.write(json.dumps({'data' : data_samples}))

class LDAExtractTopicsTask(TheTaskClass):
    today = luigi.Parameter(
           default=datetime.strftime(datetime.now(), '%Y-%m-%d')
          ) 

    def requires(self):
        return VectorizationDataTask(today=self.today)

    def run(self):
# Use tf-idf features for NMF.
        with self.input().open('r') as f:
            data = json.loads(f.read())
            data_samples = data['data']
            print("Extracting tf-idf features for NMF...")
            tfidf_vectorizer = TfidfVectorizer(max_df=0.95, min_df=2, #max_features=n_features,
                                               stop_words='english')
            t0 = time()
            tfidf = tfidf_vectorizer.fit_transform(data_samples)
            print("done in %0.3fs." % (time() - t0))

# Use tf (raw term count) features for LDA.
            print("Extracting tf features for LDA...")
            tf_vectorizer = CountVectorizer(max_df=0.95, min_df=2, max_features=n_features,
                                            stop_words='english')
            t0 = time()
            tf = tf_vectorizer.fit_transform(data_samples)
            print("done in %0.3fs." % (time() - t0))

# Fit the NMF model
            print("Fitting the NMF model with tf-idf features,"
                  "n_samples=%d and n_features=%d..."
                  % (n_samples, n_features))
            t0 = time()
            nmf = NMF(n_components=n_topics, random_state=1, alpha=.1, l1_ratio=.5).fit(tfidf)
#exit()
            print("done in %0.3fs." % (time() - t0))

            print("\nTopics in NMF model:")
            tfidf_feature_names = tfidf_vectorizer.get_feature_names()
            tw = get_top_words(nmf, tfidf_feature_names, n_top_words)
            print(tw)
            print("Fitting LDA models with tf features, n_samples=%d and n_features=%d..."
                  % (n_samples, n_features))
            lda = LatentDirichletAllocation(n_topics=n_topics, max_iter=5,
                                            learning_method='online', learning_offset=50.,
                                            random_state=0)
            t0 = time()
            lda.fit(tf)
            print("done in %0.3fs." % (time() - t0))

            print("\nTopics in LDA model:")
            tf_feature_names = tf_vectorizer.get_feature_names()
            tw = get_top_words(lda, tf_feature_names, n_top_words)
            with self.output().open('w') as out_f:
                out_f.write(json.dumps(tw))

if __name__ == '__main__':
    luigi.run()
