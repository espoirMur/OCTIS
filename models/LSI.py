from models.model import Abstract_Model
from gensim.models import lsimodel
import numpy as np
import gensim.corpora as corpora
import configuration.defaults as defaults


class LSI_Model(Abstract_Model):

    id2word = None
    id_corpus = None
    use_partitions = True
    update_with_test = False

    def info(self):
        return {
            "name": "LSI, Latent Semantic Indexing"
        }

    def partitioning(self, use_partitions, update_with_test=False):
        self.use_partitions = use_partitions
        self.update_with_test = update_with_test
        self.id2word = None
        self.id_corpus = None

    def train_model(self, dataset, hyperparameters={}, topics=10,
                    topic_word_matrix=True, topic_document_matrix=True):
        """
        Train the model and return output

        Parameters
        ----------
        dataset : dataset to use to build the model
        hyperparameters : hyperparameters to build the model
        topics : if greather than 0 returns the most significant words
                 for each topic in the output
                 Default True
        topic_word_matrix : if True returns the topic word matrix in the output
                            Default True
        topic_document_matrix : if True returns the topic document
                                matrix in the output
                                Default True

        Returns
        -------
        result : dictionary with up to 3 entries,
                 'topics', 'topic-word-matrix' and
                 'topic-document-matrix'
        """
        partition = []
        if self.use_partitions:
            partition = dataset.get_partitioned_corpus()
        else:
            partition = [dataset.get_corpus(), []]

        if self.id2word == None:
            self.id2word = corpora.Dictionary(dataset.get_corpus())

        if self.id_corpus == None:
            self.id_corpus = [self.id2word.doc2bow(
                document) for document in partition[0]]

        hyperparameters["corpus"] = self.id_corpus
        hyperparameters["id2word"] = self.id2word
        self.hyperparameters.update(hyperparameters)

        self.trained_model = lsimodel.LsiModel(**self.hyperparameters)

        result = {}

        if topic_word_matrix:
            result["topic-word-matrix"] = self._get_topic_word_matrix()

        if topics > 0:
            result["topics"] = self._get_topics_words(topics)

        if topic_document_matrix:
            result["topic-document-matrix"] = self._get_topic_document_matrix()

        if self.use_partitions:
            new_corpus = [self.id2word.doc2bow(
                document) for document in partition[1]]
            if self.update_with_test:
                self.trained_model.add_documents(new_corpus)
                self.id_corpus.extend(new_corpus)

                if topic_word_matrix:
                    result["test-topic-word-matrix"] = self._get_topic_word_matrix()

                if topics > 0:
                    result["test-topics"] = self._get_topics_words(topics)

                if topic_document_matrix:
                    result["test-topic-document-matrix"] = self._get_topic_document_matrix()

            else:
                test_document_topic_matrix = []
                for document in new_corpus:
                    test_document_topic_matrix.append(
                        self.trained_model[document])
                result["test-document-topic-matrix"] = test_document_topic_matrix

        return result

    def _get_topic_word_matrix(self):
        """
        Return the topic representation of the words
        """
        topic_word_matrix = self.trained_model.get_topics()
        normalized = []
        for words_w in topic_word_matrix:
            minimum = min(words_w)
            words = words_w - minimum
            normalized.append([float(i)/sum(words) for i in words])
        topic_word_matrix = np.array(normalized)
        return topic_word_matrix

    def _get_topics_words(self, topics):
        """
        Return the most significative words for each topic.
        """
        topic_terms = []
        for i in range(self.hyperparameters["num_topics"]):
            topic_words_list = []
            for word_tuple in self.trained_model.show_topic(i, topics):
                topic_words_list.append(word_tuple[0])
            topic_terms.append(topic_words_list)
        return topic_terms

    def _get_topic_document_matrix(self):
        """
        Return the topic representation of the
        corpus
        """
        topic_weights = self.trained_model[self.id_corpus]

        topic_document = []

        for document_topic_weights in topic_weights:

            # Find min e max topic_weights values
            minimum = document_topic_weights[0][1]
            maximum = document_topic_weights[0][1]
            for topic in document_topic_weights:
                if topic[1] > maximum:
                    maximum = topic[1]
                if topic[1] < minimum:
                    minimum = topic[1]

            # For each topic compute normalized weight
            # in the form (value-min)/(max-min)
            topic_w = []
            for topic in document_topic_weights:
                topic_w.append((topic[1]-minimum)/(maximum-minimum))
            topic_document.append(topic_w)

        return np.array(topic_document).transpose()
