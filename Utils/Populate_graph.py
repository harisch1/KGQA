from numpy import full
from py2neo import Node, Graph, Relationship, NodeMatcher
from py2neo.bulk import merge_nodes
import pickle
from tqdm import tqdm

def add_nodes(tup_ls):   
    try:
        keys = ['name', 'description', 'node_labels', 'url', 'word_vec']
        merge_nodes(graph.auto(), tup_ls, ('Node', 'name'), keys=keys)
        print('Number of nodes in graph: ', graph.nodes.match('Node').count())
    except (e):
        print(e)
    return

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


if __name__ == "__main__":
    graph = Graph('bolt://3.237.82.15:7687', name="kgqa", password="prefix-depositions-goals")
    nodes_matcher = NodeMatcher(graph)

    with open ('../data/full_node_ls', 'rb') as fp:
        full_node_ls = pickle.load(fp)

    with open ('../data/full_edge_ls', 'rb') as fp:
        full_edge_ls = pickle.load(fp)
    print(len(full_edge_ls),len(full_edge_ls))
    
    nodes = [full_node_ls[i:i + 500] for i in range(0, len(full_node_ls), 500)]
    edges = [full_edge_ls[i:i + 500] for i in range(0, len(full_edge_ls), 500)]
    # print(len(nodes[27]))
    # add_nodes(nodes[27])
    # # Split into chunks 
    # for chunk in tqdm(nodes):
    #     add_nodes(chunk)
    for chunk in tqdm(edges):
        add_edges(chunk)
