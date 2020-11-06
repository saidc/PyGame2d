import networkx as nx #py -m pip install networkx

if __name__ == "__main__":
    print("init temp.py")
    G = nx.Graph()
    e = [((1,1), (1,2), 1), ((1,4), (1,5), 1), ((1,1), (2,1), 1), ((1,2), (2,2), 1), ((2,1), (2,2), 1), ((1,4), (2,4), 1), ((1,5), (2,5), 1), ((2,4), (2,5), 1)]
    G.add_weighted_edges_from(e)
    Pa = (1,1)
    Pb = (2,2)
    result=[]
    if(G.has_node(Pa)and G.has_node(Pb)):
        if(nx.has_path(G,Pa,Pb)):
            print("exist a path")
            result = nx.dijkstra_path(G, Pa, Pb)
            print(result)
            print(result[1][1])
        else:
            print("no exist a path")
    else:
        print("node doesnt exist")
    