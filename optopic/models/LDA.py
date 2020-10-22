from optopic.models.model import Abstract_Model
import numpy as np
from gensim.models import ldamodel
import gensim.corpora as corpora
import configuration.citations as citations
import configuration.defaults as defaults


class LDA_Model(Abstract_Model):

    id2word = None
    id_corpus = None
    hyperparameters = {}
    use_partitions = True
    update_with_test = False

    def __init__(self, num_topics=100, distributed=False, chunksize=2000,
                 passes=1, update_every=1, alpha="symmetric", eta=None,
                 decay=0.5, offset=1.0, eval_every=10, iterations=50,
                 gamma_threshold=0.001, minimum_probability=0.0,
                 random_state=None, minimum_phi_value=0.1,
                 per_word_topics=False):
        """
        Initialize LDA model

        Parameters
        ----------
        num_topics (int, optional) – The number of requested latent topics to be
        extracted from the training corpus.

        distributed (bool, optional) – Whether distributed computing should be
        used to accelerate training.

        chunksize (int, optional) – Number of documents to be used in each
        training chunk.

        passes (int, optional) – Number of passes through the corpus during
        training.

        update_every (int, optional) – Number of documents to be iterated
        through for each update. Set to 0 for batch learning, > 1 for
        online iterative learning.

        alpha ({numpy.ndarray, str}, optional) – Can be set to an 1D array of
        length equal to the number of expected topics that expresses our 
        a-priori belief for the each topics’ probability. Alternatively
        default prior selecting strategies can be employed by supplying
        a string:

            ’asymmetric’: Uses a fixed normalized asymmetric prior of
            1.0 / topicno.    

            ’auto’: Learns an asymmetric prior from the corpus 
            (not available if distributed==True).

        eta ({float, np.array, str}, optional) – A-priori belief on word
        probability, this can be:

            scalar for a symmetric prior over topic/word probability,   

            vector of length num_words to denote an asymmetric user defined 
            probability for each word,  

            matrix of shape (num_topics, num_words) to assign a probability
            for each word-topic combination,    

            the string ‘auto’ to learn the asymmetric prior from the data.

        decay (float, optional) – A number between (0.5, 1] to weight what
        percentage of the previous lambda value is forgotten when each new
        document is examined.

        offset (float, optional) – Hyper-parameter that controls how much
        we will slow down the first steps the first few iterations.

        eval_every (int, optional) – Log perplexity is estimated every
        that many updates. Setting this to one slows down training by ~2x.

        iterations (int, optional) – Maximum number of iterations through the
        corpus when inferring the topic distribution of a corpus.

        gamma_threshold (float, optional) – Minimum change in the value of the
        gamma parameters to continue iterating.

        minimum_probability (float, optional) – Topics with a probability lower
        than this threshold will be filtered out.

        random_state ({np.random.RandomState, int}, optional) – Either a
        randomState object or a seed to generate one. Useful for reproducibility.

        minimum_phi_value (float, optional) – if per_word_topics is True, this
        represents a lower bound on the term probabilities.

        per_word_topics (bool) – If True, the model also computes a list of
        topics, sorted in descending order of most likely topics for each
        word, along with their phi values multiplied by the feature length.

        """
        self.hyperparameters["num_topics"] = num_topics
        self.hyperparameters["distributed"] = distributed
        self.hyperparameters["chunksize"] = chunksize
        self.hyperparameters["passes"] = passes
        self.hyperparameters["update_every"] = update_every
        self.hyperparameters["alpha"] = alpha
        self.hyperparameters["eta"] = eta
        self.hyperparameters["decay"] = decay
        self.hyperparameters["offset"] = offset
        self.hyperparameters["eval_every"] = eval_every
        self.hyperparameters["iterations"] = iterations
        self.hyperparameters["gamma_threshold"] = gamma_threshold
        self.hyperparameters["minimum_probability"] = minimum_probability
        self.hyperparameters["random_state"] = random_state
        self.hyperparameters["minimum_phi_value"] = minimum_phi_value
        self.hyperparameters["per_word_topics"] = per_word_topics

    def info(self):
        """
        Returns model informations
        """
        return {
            "citation": citations.models_LDA,
            "name": "LDA, Latent Dirichlet Allocation"
        }

    def hyperparameters_info(self):
        """
        Returns hyperparameters informations
        """
        return defaults.LDA_hyperparameters_info

    def set_hyperparameters(self, **kwargs):
        """
        Set model hyperparameters
        """
        super().set_hyperparameters(**kwargs)
        # Allow alpha to be a float in case of symmetric alpha
        if "alpha" in kwargs:
            if isinstance(kwargs["alpha"], float):
                self.hyperparameters["alpha"] = [
                    kwargs["alpha"]
                ] * self.hyperparameters["num_topics"]

    def partitioning(self, use_partitions, update_with_test=False):
        """
        Handle the partitioning system to use and reset the model to perform
        new evaluations

        Parameters
        ----------
        use_partitions: True if train/set partitioning is needed, False
                        otherwise
        update_with_test: True if the model should be updated with the test set,
                          False otherwise
        """
        self.use_partitions = use_partitions
        self.update_with_test = update_with_test
        self.id2word = None
        self.id_corpus = None

    def train_model(self, dataset, hyperparameters={}, top_words=10,
                    topic_word_matrix=True, topic_document_matrix=True):
        """
        Train the model and return output

        Parameters
        ----------
        dataset : dataset to use to build the model
        hyperparameters : hyperparameters to build the model
        top_words : if greather than 0 returns the most significant words
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
        if self.use_partitions:
            train_corpus, test_corpus = dataset.get_partitioned_corpus(use_validation=False)
        else:
            train_corpus = dataset.get_corpus()

        if self.id2word is None:
            self.id2word = corpora.Dictionary(dataset.get_corpus())

        if self.id_corpus is None:
            self.id_corpus = [self.id2word.doc2bow(document)
                              for document in train_corpus]

        if "num_topics" not in hyperparameters:
            hyperparameters["num_topics"] = self.hyperparameters["num_topics"]

        # Allow alpha to be a float in case of symmetric alpha
        if "alpha" in hyperparameters:
            if isinstance(hyperparameters["alpha"], float):
                hyperparameters["alpha"] = [
                    hyperparameters["alpha"]
                ] * hyperparameters["num_topics"]

        hyperparameters["corpus"] = self.id_corpus
        hyperparameters["id2word"] = self.id2word
        self.hyperparameters.update(hyperparameters)

        self.trained_model = ldamodel.LdaModel(**self.hyperparameters)

        result = {}

        if topic_word_matrix:
            result["topic-word-matrix"] = self.trained_model.get_topics()

        if top_words > 0:
            topics_output = []
            for topic in result["topic-word-matrix"]:
                top_k = np.argsort(topic)[-top_words:]
                top_k_words = list(reversed([self.id2word[i] for i in top_k]))
                topics_output.append(top_k_words)
            result["topics"] = topics_output

        if topic_document_matrix:
            result["topic-document-matrix"] = self._get_topic_document_matrix()

        if self.use_partitions:
            new_corpus = [self.id2word.doc2bow(
                document) for document in test_corpus]
            if self.update_with_test:
                self.trained_model.update(new_corpus)
                self.id_corpus.extend(new_corpus)

                if topic_word_matrix:
                    result["test-topic-word-matrix"] = self.trained_model.get_topics()

                if top_words > 0:
                    topics_output = []
                    for topic in result["test-topic-word-matrix"]:
                        top_k = np.argsort(topic)[-top_words:]
                        top_k_words = list(
                            reversed([self.id2word[i] for i in top_k]))
                        topics_output.append(top_k_words)
                    result["test-topics"] = topics_output

                if topic_document_matrix:
                    result["test-topic-document-matrix"] = self._get_topic_document_matrix()

            else:
                test_document_topic_matrix = []
                for document in new_corpus:
                    document_topics_tuples = self.trained_model[document]
                    document_topics = np.zeros(
                        self.hyperparameters["num_topics"])
                    for single_tuple in document_topics_tuples:
                        document_topics[single_tuple[0]] = single_tuple[1]

                    test_document_topic_matrix.append(document_topics)
                result["test-topic-document-matrix"] = np.array(
                    test_document_topic_matrix).transpose()
        return result

    def _get_topics_words(self, topk):
        """
        Return the most significative words for each topic.
        """
        topic_terms = []
        for i in range(self.hyperparameters["num_topics"]):
            topic_words_list = []
            for word_tuple in self.trained_model.get_topic_terms(i, topk):
                topic_words_list.append(self.id2word[word_tuple[0]])
            topic_terms.append(topic_words_list)
        return topic_terms

    def _get_topic_document_matrix(self):
        """
        Return the topic representation of the
        corpus
        """
        doc_topic_tuples = []
        for document in self.id_corpus:
            doc_topic_tuples.append(
                self.trained_model.get_document_topics(document,
                                                       minimum_probability=0))

        topic_document = np.zeros((
            self.hyperparameters["num_topics"],
            len(doc_topic_tuples)))

        for ndoc in range(len(doc_topic_tuples)):
            document = doc_topic_tuples[ndoc]
            for topic_tuple in document:
                topic_document[topic_tuple[0]][ndoc] = topic_tuple[1]
        return topic_document