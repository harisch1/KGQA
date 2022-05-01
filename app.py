import re
from Question_Extraction._QA import QuestionAnswer
from Utils.Scrape_Data import scrape_wikipedia
from Utils.kg_populate import generateGraph
import json
from wikipedia import search


class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

class App:
    def __init__(self):
        super(App, self).__init__()
        self.qna = QuestionAnswer()

    def runApp(self):

        print(color.BLUE + "Capstone Project by Muhammad Haris Choudhary")
        print("Question Answering System Over Knowledge Graphs (Art Domain)"+ color.END)
        print(color.RED + "\n Enter 'End' at anytime to exit."+ color.END)
        while (True):
            try: 
                choice = input(color.BOLD + """ Please input your question or input "New Topic" for new data \n Q> """ + color.END)
                if choice == "END": return
                if choice.lower() == "new topic":
                    topic = input(color.BOLD + """ Please input the new topic \n T> """ + color.END)
                    if topic == "END": return
                    try:
                        with open('./data/text_dump.json', 'r') as fp:
                            data = json.load(fp)
                        name = search(topic)
                        if name[0] in data.keys():
                            print("  > Topic Already Exists")
                        else:
                            new_data = scrape_wikipedia(topic)
                            if new_data != None:
                                data.update(new_data)
                                print(f'  > {len(new_data)} new page(s) found!')
                                with open('./data/text_dump.json', 'w') as fp:
                                    json.dump(data, fp)
                                nodes = generateGraph(new_data)
                                print(color.GREEN + f'  > Data added to the graph! New number of nodes is {nodes}' + color.END)
                            else:
                                print("  > No data found!")
                    except:
                        print(color.GREEN+"  > No data found!"+color.END)
                else:
                    answer = self.qna.answer(choice)
                    print(" A> " + answer)
            except: 
                continue


if __name__ == "__main__":
    app = App()
    app.runApp()