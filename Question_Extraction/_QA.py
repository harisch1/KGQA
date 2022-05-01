import json
import re
import inflect
import pandas as pd
import spacy
from Question_Extraction._complex import ComplexFunc
from py2neo import Graph
from py2neo.matching import *
# activated = spacy.prefer_gpu()

class QuestionAnswer:
    """docstring for QuestionAnswer."""

    def __init__(self):
        super(QuestionAnswer, self).__init__()
        self.complex = ComplexFunc()
        self.nlp = spacy.load('en_core_web_lg')
        self.p = inflect.engine()
        self.graph = Graph('bolt://localhost:7687', auth = ("neo4j", "tester"))
        self.nodes_matcher = NodeMatcher(self.graph)
        self.relationship_matcher = RelationshipMatcher(self.graph)
    
    def answer(self, question):
        p=None
        try:
            p = self.complex.question_pairs(question.lower())[0]
        except: 
            print()
        if p == [] or p is None:
            quest = self.nlp(question)
            p = ['']*6
            for tok in quest:
                if tok.dep_ == 'compound' :
                        p[0] = tok.text
                elif tok.dep_ == 'nsubj' :
                    p[0] += ' ' + tok.text
                elif tok.dep_ == 'ROOT':
                    p[1] = tok.text
                elif tok.dep_ == 'attr':
                    p[-1] = tok.text.lower()
                if "when" in question.lower():
                    p[-1] = "when"
                    if tok.dep_ == 'auxpass' :
                        p[4] = tok.text


        if p[0] == 'unknown' or p[0] == '' or p[0] is None:
            quest = self.nlp(q)
            for tok in quest:
                if tok.ent_type_ == 'PERSON' :
                    if p[0] == 'unknown':
                        p[0] = tok.text
                    else: p[0] += ' ' + tok.text
        
        
        for i in range(len(p)):
            p[i] = p[i].replace('-', " ")

        if 'birth' in question.split():
            p[1] = 'be' 

        if str(p[1].lower()) == "born":
            qRel = 'be' 
        else:
            rel = self.nlp(p[1])
            for tok in rel:
                qRel = tok.lemma_
    

        objectQ = p[3]
        # subList = []
        # timeQ = str(p[4]).lower()
        # placeQ = str(p[5]).lower()
        res = ''
        cypher = ''

        # print(p)
        # Looking for a person or description of a person
        if 'who' in p:
            if objectQ != '':
                cypher = f'match (n)-[r:{qRel} | {p[1].lower()}]-(m) where n.name contains "{objectQ}" or n.name contains "{p[0].lower()}" return m.name'
            else:
                cypher = f'match (n)-[r:{qRel} | {p[1].lower()}]-(m) where n.name contains "{p[0].split()[0].lower()}" return m.name'
            # print("It's who\n"+cypher)
            query = self.graph.run(cypher)
            subt = self.nlp(p[0])
            for i in subt: pers = i.ent_type_
            if query != None:
                for node in query:
                    doc = self.nlp(str(node))
                    for i in doc:
                        # print(i.text + " - \t "+ i.ent_type_)
                        if i.ent_type_ == "PERSON" and (pers != "PERSON" and pers != "WORK_OF_ART") :
                            res += node[0] + ","
                        elif i.ent_type_ == "NORP":
                            res += node[0] +','
                if res != '':
                    return res[:-1]
            return "Answer Not Found"


        # Return a Location
        elif 'where' in p:
            cypher = f'match (n)-[r:{qRel} | {p[1].lower()}]-(m) where n.name contains "{p[0].lower()}" return m.name as Result'
            query = self.graph.run(cypher)
            if query != None:
                for node in query:
                    doc = self.nlp(str(node))
                    for i in doc:
                        if i.ent_type_ == "GPE":
                            res += node[0] + ","
                        # if i.ent_type_ == "NORP":
                        #     res += node[0] +','
                if res != '':
                    return res[:-1]
            return "Answer Not Found"

        elif 'what' in p:
            splittedQ = question.split()
            if "place" in splittedQ:
                cypher = f'match (n)-[r:{qRel} | {p[1].lower()}]-(m) where n.name contains "{p[0].lower()}" return m.name as Result'
                query = self.graph.run(cypher)
                if query != 0:
                    for node in query:
                        doc = self.nlp(str(node))
                        for i in doc:
                            if i.ent_type_ == "GPE":
                                res += node[0] + ","
                            elif i.ent_type_ == "ORG":
                                res += node[0] + ","
                           
                    if res != '':
                        return res
                    return query
            else:
                cypher = f'match (n)-[r:{qRel} | {p[1].lower()}]-(m) where n.name contains "{p[0].lower()}" and "Thing" in m.node_labels return m.name as Result'
            
            # if "paint" in splittedQ:


            return "Answer Not Found"

        # Return a Location
        elif 'when' in p:
            cypher = f'match (n)-[r:{qRel} | {p[1].lower()}]-(m) where n.name contains "{p[0].lower()}" return m.name as Result'
            query = self.graph.run(cypher)
            if query != None:
                for node in query:
                    doc = self.nlp(str(node))
                    for i in doc:
                        if i.ent_type_ == "DATE":
                            res += node[0] + ","
                        # if i.ent_type_ == "NORP":
                        #     res += node[0] +','
                if res != '':
                    return res[:-1]
            return "Answer Not Found"

        else:
            if "name" in p:
                cypher = f'match (n)-[]-(m) where n.name contains "{p[4].lower()}" and ("Person" in m.node_labels or "Subject" in m.node_labels) return m.name'
                query = self.graph.run(cypher)
                if query != None:
                    names = []
                    for name in query:
                        doc = self.nlp(str(name))
                        for i in doc:
                            if i.ent_type_ == "PERSON":
                                if name.values() not in names:
                                    names.append(name.values())
                    return names

            else:
                cypher = f'match (n)-[r:{qRel.lower()} | {p[1].lower()}]-(m) where n.name contains "{p[0].lower()}"  return m.name'
                query = self.graph.run(cypher)
            return query
        