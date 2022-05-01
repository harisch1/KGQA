import json
import re
import urllib
from pprint import pprint
from tqdm import tqdm


from py2neo import Node, Graph, Relationship, NodeMatcher
from py2neo.bulk import merge_nodes

import numpy as np


import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from spacy.matcher import Matcher
from spacy.tokens import Doc, Span, Token
# import warnings
# with warnings.catch_warnings():
#     warnings.simplefilter("ignore", UserWarning)
#     activated = spacy.prefer_gpu()
    
    

# print(spacy.__version__)

import os
directory = os.getcwd()

# print(directory)
# activated = spacy.prefer_gpu()
# print(activated)

SUBJECTS = ["nsubj", "nsubjpass", "csubj", "csubjpass", "agent", "expl"]
VERBS = ['ROOT', 'advcl']
OBJECTS = ["dobj", "dative", "attr", "oprd", 'pobj']
ENTITY_LABELS = ['PERSON', 'NORP', 'GPE', 'ORG', 'FAC', 'LOC', 'PRODUCT', 'EVENT', 'WORK_OF_ART']

api_key = open('./keys/.api_key').read()

non_nc = spacy.load('en_core_web_lg')

nlp = spacy.load('en_core_web_lg')
nlp.add_pipe('merge_noun_chunks')
graph = Graph('bolt://localhost:7687', auth = ("neo4j", "tester"))
nodes_matcher = NodeMatcher(graph)
def query_google(query, api_key, limit=10, indent=True, return_lists=True):
    
    text_ls = []
    node_label_ls = []
    url_ls = []
    
    params = {
        'query': query,
        'limit': limit,
        'indent': indent,
        'key': api_key,
    }   
    
    service_url = 'https://kgsearch.googleapis.com/v1/entities:search'
    url = service_url + '?' + urllib.parse.urlencode(params)
    response = json.loads(urllib.request.urlopen(url).read())
    
    if return_lists:
        for element in response['itemListElement']:

            try:
                node_label_ls.append(element['result']['@type'])
            except:
                node_label_ls.append('')

            try:
                text_ls.append(element['result']['detailedDescription']['articleBody'])
            except:
                text_ls.append('')
                
            try:
                url_ls.append(element['result']['detailedDescription']['url'])
            except:
                url_ls.append('')
                
        return text_ls, node_label_ls, url_ls
    
    else:
        return response

def remove_special_characters(text):
    
    regex = re.compile(r'[\n\r\t]')
    clean_text = regex.sub(" ", text)
    
    return clean_text


def remove_stop_words_and_punct(text, print_text=False):
    
    result_ls = []
    rsw_doc = non_nc(text)
    
    for token in rsw_doc:
        if print_text:
            print(token, token.is_stop)
            print('--------------')
        if not token.is_stop and not token.is_punct:
            result_ls.append(str(token))
    
    result_str = ' '.join(result_ls)

    return result_str


def create_svo_lists(doc, print_lists):
    
    subject_ls = []
    verb_ls = []
    object_ls = []

    for token in doc:
        if token.dep_ in SUBJECTS:
            subject_ls.append((token.lower_, token.idx))
        elif token.dep_ in VERBS:
            verb_ls.append((token.lemma_, token.idx))
        elif token.dep_ in OBJECTS:
            object_ls.append((token.lower_, token.idx))

    if print_lists:
        print('SUBJECTS: ', subject_ls)
        print('VERBS: ', verb_ls)
        print('OBJECTS: ', object_ls)
    
    return subject_ls, verb_ls, object_ls


def remove_duplicates(tup, tup_posn):
    
    check_val = set()
    result = []
    
    for i in tup:
        if i[tup_posn] not in check_val:
            result.append(i)
            check_val.add(i[tup_posn])
            
    return result


def remove_dates(tup_ls):
    
    clean_tup_ls = []
    for entry in tup_ls:
        if not entry[2].isdigit():
            clean_tup_ls.append(entry)
    return clean_tup_ls


def create_svo_triples(text, print_lists=False):
    
    clean_text = remove_special_characters(text)
    doc = nlp(clean_text)
    subject_ls, verb_ls, object_ls = create_svo_lists(doc, print_lists=print_lists)
    
    graph_tup_ls = []
    dedup_tup_ls = []
    clean_tup_ls = []

    for subj in subject_ls: 
        for obj in object_ls:
            
            dist_ls = []
            
            for v in verb_ls:
                
                # Assemble a list of distances between each object and each verb
                dist_ls.append(abs(obj[1] - v[1]))
                
            # Get the index of the verb with the smallest distance to the object 
            # and return that verb
            index_min = min(range(len(dist_ls)), key=dist_ls.__getitem__)
            
            # Remve stop words from subjects and object.  Note that we do this a bit
            # later down in the process to allow for proper sentence recognition.

            no_sw_subj = remove_stop_words_and_punct(subj[0])
            no_sw_obj = remove_stop_words_and_punct(obj[0])
            
            # Add entries to the graph iff neither subject nor object is blank
            if no_sw_subj and no_sw_obj:
                tup = (no_sw_subj, verb_ls[index_min][0], no_sw_obj)
                graph_tup_ls.append(tup)
 
        #clean_tup_ls = remove_dates(graph_tup_ls)

    
    dedup_tup_ls = remove_duplicates(graph_tup_ls, 2)
    clean_tup_ls = remove_dates(dedup_tup_ls)
    
    return clean_tup_ls

def get_obj_properties(tup_ls):
    
    init_obj_tup_ls = []
    
    for tup in tup_ls:

        try:
            text, node_label_ls, url = query_google(tup[2], api_key, limit=1)
            new_tup = (tup[0], tup[1], tup[2], text[0], node_label_ls[0], url[0])
        except:
            new_tup = (tup[0], tup[1], tup[2], [], [], [])
        
        init_obj_tup_ls.append(new_tup)
        
    return init_obj_tup_ls


def add_layer(tup_ls):

    svo_tup_ls = []
    
    for tup in tup_ls:
        
        if tup[3]:
            svo_tup = create_svo_triples(tup[3])
            svo_tup_ls.extend(svo_tup)
        else:
            continue
    
    return get_obj_properties(svo_tup_ls)
        

def subj_equals_obj(tup_ls):
    
    new_tup_ls = []
    
    for tup in tup_ls:
        if tup[0] != tup[2]:
            new_tup_ls.append((tup[0], tup[1], tup[2], tup[3], tup[4], tup[5]))
            
    return new_tup_ls


def check_for_string_labels(tup_ls):
    # This is for an edge case where the object does not get fully populated
    # resulting in the node labels being assigned to string instead of list.
    # This may not be strictly necessary and the lines using it are commnted out
    # below.  Run this function if you come across this case.
    
    clean_tup_ls = []
    
    for el in tup_ls:
        if isinstance(el[2], list):
            clean_tup_ls.append(el)

    return clean_tup_ls


def create_word_vectors(tup_ls):

    new_tup_ls = []
    
    for tup in tup_ls:
        if tup[3]:
            doc = nlp(tup[3])
            new_tup = (tup[0], tup[1], tup[2], tup[3], tup[4], tup[5], doc.vector)
        else:
            new_tup = (tup[0], tup[1], tup[2], tup[3], tup[4], tup[5], np.random.uniform(low=-1.0, high=1.0, size=(300,)))
        new_tup_ls.append(new_tup)
        
    return new_tup_ls

def dedup(tup_ls):
    
    visited = set()
    output_ls = []
    
    for tup in tup_ls:
        if not tup[0] in visited:
            visited.add(tup[0])
            output_ls.append((tup[0], tup[1], tup[2], tup[3], tup[4]))
    return output_ls


def convert_vec_to_ls(tup_ls):
    
    vec_to_ls_tup = []
    
    for el in tup_ls:
        vec_ls = [float(v) for v in el[4]]
        tup = (el[0], el[1], el[2], el[3], vec_ls)
        vec_to_ls_tup.append(tup)
        
    return vec_to_ls_tup




def edge_tuple_creation(text):
    
    initial_tup_ls = create_svo_triples(text)
    init_obj_tup_ls = get_obj_properties(initial_tup_ls)
    new_layer_ls = add_layer(init_obj_tup_ls)
    starter_edge_ls = init_obj_tup_ls + new_layer_ls
    edge_ls = subj_equals_obj(starter_edge_ls)
    edges_word_vec_ls = create_word_vectors(edge_ls)
    
    return edges_word_vec_ls


def node_tuple_creation(edges_word_vec_ls):
    
    orig_node_tup_ls = [(edges_word_vec_ls[0][0], '', ['Subject'], '', np.random.uniform(low=-1.0, high=1.0, size=(300,)))]
    obj_node_tup_ls = [(tup[2], tup[3], tup[4], tup[5], tup[6]) for tup in edges_word_vec_ls]
    full_node_tup_ls = orig_node_tup_ls + obj_node_tup_ls
    cleaned_node_tup_ls = check_for_string_labels(full_node_tup_ls)
    #dedup_node_tup_ls = dedup(cleaned_node_tup_ls)
    dedup_node_tup_ls = cleaned_node_tup_ls
    node_tup_ls = convert_vec_to_ls(dedup_node_tup_ls)
    
    return node_tup_ls

def get_nodes_edges(text):
    edges_word_vec_ls = edge_tuple_creation(text) 
    node_tup_ls = node_tuple_creation(edges_word_vec_ls)
    return edges_word_vec_ls, node_tup_ls

# Adding nodes to the Neo4j database
def add_nodes(tup_ls):   
    try:
        keys = ['name', 'description', 'node_labels', 'url', 'word_vec']
        merge_nodes(graph.auto(), tup_ls, ('Node', 'name'), keys=keys)
        # print('Number of nodes in graph: ', graph.nodes.match('Node').count())
    except (e):
        print(e)
    # return graph.nodes.match('Node').count()

def add_edges(edge_ls):
    
    edge_dc = {} 
    
    # Group tuple by verb
    # Result: {verb1: [(sub1, v1, obj1), (sub2, v2, obj2), ...],
    #          verb2: [(sub3, v3, obj3), (sub4, v4, obj4), ...]}
    
    for tup in edge_ls: 
        if tup[1] in edge_dc: 
            edge_dc[tup[1]].append((tup[0], tup[1], tup[2])) 
        else: 
            edge_dc[tup[1]] = [(tup[0], tup[1], tup[2])] 
    
    for edge_labels, tup_ls in edge_dc.items():   # k=edge labels, v = list of tuples
        
        tx = graph.begin()
        
        for el in tup_ls:
            source_node = nodes_matcher.match(name=el[0]).first()
            target_node = nodes_matcher.match(name=el[2]).first()
            if not source_node:
                source_node = Node('Node', name=el[0])
                tx.create(source_node)
            if not target_node:
                try:
                    target_node = Node('Node', name=el[2], node_labels=el[4], url=el[5], word_vec=el[6])
                    tx.create(target_node)
                except:
                    continue
            try:
                rel = Relationship(source_node, edge_labels, target_node)
            except:
                continue
            tx.create(rel)
        tx.commit()
    
    return

def generateGraph(text_dump):
    full_edge_ls, full_node_ls = [], []

    for text in tqdm(text_dump.items()):
        try: 
            edge_ls, node_ls = get_nodes_edges(text[1])
            dedup_node_tup_ls = dedup(node_ls)
            add_nodes(dedup_node_tup_ls)
            add_edges(edge_ls)
            # Remove Duplicates
            graph.run("MATCH (n:Node) WITH n.name AS name, COLLECT(n) AS nodes WHERE SIZE(nodes)>1 FOREACH (el in nodes | DETACH DELETE el)")
        except:
            print(f'cant do {text[0]}')
    return graph.nodes.match('Node').count()


if __name__ == '__main__':

    with open('../data/text_dump.json', 'r') as fp:
        text_dump = json.load(fp)

    graph = Graph('bolt://localhost:7687', auth = ("neo4j", "tester"))
    nodes_matcher = NodeMatcher(graph)

    generateGraph(text_dump)

    
    # with open('../data/full_node_ls', 'wb') as fp:
    #     pickle.dump(full_node_ls, fp)

    # with open('../data/full_edge_ls', 'wb') as fp:
    #     pickle.dump(full_edge_ls, fp)



