#visualize the networkx DiGraph using a Dash dashboard

#General warning: Note that with this dashboard, the edge arrows drawn are infact symmetrical and angled correctly.
#And are all the same distance/size… they just don’t always look that way because the scaling of the x-axis
#    isn’t the same scaling of the y-axis all the time (depending on how the user draws the box to zoom and the default aspect ratios).


import pandas as pd
import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
import plotly.graph_objs as go

import networkx as nx
import pygraphviz
import math
import numpy as np

import matplotlib.pyplot as plt
from scipy.special import binom

def Bernstein(n, k):
    """Bernstein polynomial.
        
        """
    coeff = binom(n, k)
    
    def _bpoly(x):
        return coeff * x ** k * (1 - x) ** (n - k)
    
    return _bpoly


def Bezier(points, num=200):
    """Build Bézier curve from points.
        
        """
    N = len(points)
    t = np.linspace(0, 1, num=num)
    curve = np.zeros((num, 2))
    for ii in range(N):
        curve += np.outer(Bernstein(N - 1, ii)(t), points[ii])
    return curve

#load in networkx graph to access graph information
G = nx.read_gpickle("Climate_Mind_DiGraph.gpickle")

#pos = nx.nx_agraph.graphviz_layout(G, prog='dot')

#convert the network x graph to a graphviz graph
N = nx.nx_agraph.to_agraph(G)

#change the graphviz graph settings to make the graph layout of edges and nodes as we want
N.edge_attr.update(splines="curved",directed=True)
N.layout(prog='dot')

#output the graphviz graph layout details as a string file to parse and vizualize using native python plotly and dash
s = N.string() #this string contains the coordinates for the edges so they aren't just straight lines but curve to avoid going through other nodes

#option to save graphviz graph file if desired. Not necessary though.
#N.write('edges_spline_layout_coordinates.txt') #this file also has the coordinates for the splines for the edges that curve around the nodes instead of going through the nodes

#parse the graphviz graph string for the layout information we need
data = s.split(";\n")
#remove header and footer content
header = data[0:3]
content = data[3:len(data)-1]


#go through each item in 'content', and separate into either node or edge object
N_nodes = []
N_edges = []
for item in content:
    if " -> " in item:
        N_edges.append(item)
    else:
        N_nodes.append(item)

#populate node graph layout details from graphviz
N_node_details = []
for N_node in N_nodes:
    name = N_node.split('\t')[1].strip("\"")
    height = float(N_node.split('\n\t\t')[2].replace("height=","").strip(','))
    position = N_node.split('\n\t\t')[4].replace("pos=\"","").strip('",').split(",")
    position = [float(thing) for thing in position]
    width = float(N_node.split('\n\t\t')[6].replace("width=","").strip(']'))
    N_node_details.append([name,height,position,width])

#populate edge graph layout details from graphviz
N_edge_details = []
for edge in N_edges:
    node1,node2 = edge.split('\t')[1].split(' -> ')
    node1 = node1.strip("\"")
    node2 = node2.strip("\"")
    print(edge)
    position = edge.split('\t')[2].replace('[pos="e,',"").replace("\\","").replace("\n","").strip("\",").split(" ")
    print(position)
    position = [[float(thing.split(",")[0]),float(thing.split(",")[1])] for thing in position]
    type = edge.split('\n\t\t')[2].replace("type=","").strip(']')
    N_edge_details.append([node1,node2,position,type])


#divide the x and y coordinates into separate lists
node_x_list = []
for node in N_node_details:
    node_x_list.append(node[2][0])
node_y_list = []
for node in N_node_details:
    node_y_list.append(node[2][1])

#links to help undertand dash better if needed
#https://plotly.com/python/line-charts/
#https://plotly.com/python/shapes/
#radio icons and dropdown menus
#https://www.datacamp.com/community/tutorials/learn-build-dash-python

#blank figure object
fig = go.Figure()

#add scatter trace of text labels to the figure object
fig.add_trace(go.Scatter(
                         x=node_x_list,
                         y=node_y_list,
                         text=[node[0] for node in N_node_details],
                         mode="text",
                         textfont=dict(
                                       color="black",
                                       size=8.5,
                                       family="sans-serif",
                                       )
                         ))
                         
#Add node traces as ovals to the figure object
#Note how 72 is the conversion of graphviz point scale to inches scale
for node in N_node_details:
    fig.add_shape(
              type="circle",
              x0=node[2][0]-0.5*node[3]*72,
              y0=node[2][1]-0.5*node[1]*72,
              x1=node[2][0]+0.5*node[3]*72,
              y1=node[2][1]+0.5*node[1]*72
              )

#divide graphviz edge curve coordinates into groups of coordinates to help draw edges as correct spline curves (cubic B splines)
def divide_into_4s(input):
    size = 4
    step = 3
    output = [input[i : i + size] for i in range(1, len(input)-2, 3)]
    return(output)

#unit vector to help with edge geometry (specifically drawing arrows)
def unit_vector(v):
    return v / np.linalg.norm(v)

#adding edges (and arrows and tees to edges)
for edge in N_edge_details:
    start = edge[2][0]
    end = edge[2][1]
    backwards = edge[2][2:][::-1]
    edge_fix = [start]+backwards+[end] #graphviz has weird edge coordinate format that doesn't have coordinates in correct order
    #approximate the B spline curve
    #see the following websites to better understand:
    #http://graphviz.996277.n3.nabble.com/how-to-draw-b-spline-td1328.html
    #https://stackoverflow.com/questions/28279060/splines-with-python-using-control-knots-and-endpoints
    #https://stackoverflow.com/questions/53934876/how-to-draw-a-graphviz-spline-in-d3
    #https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-837-computer-graphics-fall-2012/lecture-notes/MIT6_837F12_Lec01.pdf
    #https://github.com/kawache/Python-B-spline-examples
    #https://stackoverflow.com/questions/12643079/b%C3%A9zier-curve-fitting-with-scipy
    #https://nurbs-python.readthedocs.io/en/latest/module_bspline.html
    blocks = divide_into_4s(edge_fix)
    path = [] #path to draw
    path.append(start)
    for chunk in blocks:
        curve = Bezier(chunk,200)
        path = path + curve.tolist()

    #add arrow adornment using linear algebra
    if edge[3] == 'causes_or_promotes':
        #A,B = [path[-20],path[-1]]
        A,B = [path[20],path[0]]
        A = np.array(A)
        B = np.array(B)
        height = 5*math.sqrt(3)
        theta = 45
        width = height*math.tan(theta/2)
        U = (B - A)/np.linalg.norm(B-A)
        V = np.array((-1*U[1], U[0]))
        v1 = B - height*U + width*V
        v2 = B - height*U - width*V
        adornment_to_add = [v1.tolist()]+[B]+[v2.tolist()]
        xpoint = [ coordinate[0] for coordinate in adornment_to_add ]
        ypoint = [ coordinate[1] for coordinate in adornment_to_add ]
        fig.add_trace(go.Scatter(x=xpoint,y=ypoint, line_shape='linear',mode='lines'))

        #add tee adornment using linear algebra
    if edge[3] == 'is_inhibited_or_prevented_or_blocked_or_slowed_by':
        #B,A = [path[0],path[1]]
        B,A = [path[-1],path[2]]
        A = np.array(A)
        B = np.array(B)
        height = 0
        width = 10
        U = (B - A)/np.linalg.norm(B-A)
        V = np.array((-1*U[1], U[0]))
        v1 = B - height*U + width*V
        v2 = B - height*U - width*V
        adornment_to_add = [v1.tolist()]+[B]+[v2.tolist()]
        xpoint = [ coordinate[0] for coordinate in adornment_to_add ]
        ypoint = [ coordinate[1] for coordinate in adornment_to_add ]
        fig.add_trace(go.Scatter(x=xpoint,y=ypoint, line_shape='linear',mode='lines'))

    #add edge spline trace to the figure object
    xp = [ coordinate[0] for coordinate in path ]
    yp = [ coordinate[1] for coordinate in path ]
    fig.add_trace(go.Scatter(x=xp,y=yp, line_shape='spline'))

#change the x and y axis ranges to be the values found in the 'header' of the graphviz graph layout string
fig.update_xaxes(range=[0, 8395.7])
fig.update_yaxes(range=[0, 1404])

#may need to add this back in later to help adjust the first look of the dashboard
#fig.update_layout(
                  #autosize=False,
                  #width=8395.7,
                  #height=1404,
                  #yaxis = dict(
                  #scaleanchor = "x",
                  #            scaleratio = /1404,
#            ))

#add scroll zooming as a feature
config = dict({'scrollZoom': True})
fig.show(config=config)


################### START OF DASH APP ###################
app = dash.Dash()

# NEED TO ADD HTML formating and maybe CSS

# NEED TO ADD in callback features to make the dashboard interactive!!!



if __name__ == '__main__':
    app.run_server(debug=False)
