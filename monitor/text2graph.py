import re
from collections import deque
libcFunctions = [
       # // Memory allocation
        "malloc", "calloc", "realloc", "free",
        #// Input/Output
        "printf", "__isoc99_scanf", "fprintf", "fscanf", "fopen", "fclose", "fread", "fwrite",
       # // String manipulation
        "strcpy", "strncpy", "strcat", "strncat", "strcmp", "strncmp", "strlen",
       # // Memory manipulation
        "memcpy", "memmove", "memset", "memcmp",
       # // Mathematical functions
        "abs", "labs", "div", "ldiv", "sqrt", "pow", "exp", "log", "sin", "cos", "tan",
       # // Time-related functions
        "time", "ctime", "gmtime", "localtime", "strftime",
       # // Process control
        "exit", "abort", "atexit",
        #// Environment
        "getenv", "system",
        #// Sorting and searching
        "qsort", "bsearch",
       # // Integer arithmetics
        "atoi", "atol", "strtol", "strtoul",
        #// Random number generation
        "rand", "srand",
       # // Multibyte characters
        "mblen", "mbtowc", "wctomb",
      #  // Error handling
        "perror", "strerror",
        "socket","dup","write","open","uname"
    ]
# def epsilon_closure(graph, start_vertex):
#     closure = set([start_vertex])
#     queue = deque([start_vertex])
    
#     while queue:
#         vertex = queue.popleft()
#         print(queue)
#         for neighbor, label in graph[vertex]:
#             if (label not in libcFunctions) and neighbor not in closure:
#                 closure.add(neighbor)
#                 queue.append(neighbor)
    
#     return closure

def epsilon_closure(graph, start_vertex):
    closure = set([start_vertex])
    queue = deque([start_vertex])
    
    while queue:
        print("once")
        vertex = queue.popleft()
        for neighbor, label in graph[vertex]:
            if (label not in libcFunctions) and neighbor not in closure:
                closure.add(neighbor)
                queue.append(neighbor)
    
    return closure
def construct_graph(path): 
 fd = open(path,'r')
 str = fd.read()
 graph = {}
 pattern = r'(\d+) -> (\d+) \[label="(\w+)"\]'
 first = True 
 start = 0 
 for x in str.splitlines():
     delta1 = re.search(r"start:(\d+)",x)
     if delta1 : 
        start = delta1.group(1)
     delta = re.search(pattern,x)
     u=0
     v=0
     w=""
     if delta : 
      u = int(delta.group(1))
      v = int(delta.group(2))
      w = delta.group(3)
      if  u in graph.keys() :
         graph[u].append([v,w])
      else :
         graph[u] = [[v,w]]

    
 return graph,start

epsilon_closures = [{}]
def closures(graph):
 for vertex in graph.keys():
    epsilon_closures.append(epsilon_closure(graph,int(vertex)))
 return epsilon_closures
# graph,start = construct_graph('/home/huzam/assignment_5/secure_policy_1.dot')
# print(graph)
# print(epsilon_closure(graph,31))