class FAQ:
    def __init__(self, question, answer):
        self.__question = question
        self.__answer = answer
        self.__faq_id = None

    def get_question(self):
        return self.__question

    def get_answer(self):
        return self.__answer

    def get_faq_id(self):
        return self.__faq_id

    def set_question(self, question):
        self.__question = question

    def set_answer(self, answer):
        self.__answer = answer

    def set_faq_id(self, faq_id):
        self.__faq_id = faq_id