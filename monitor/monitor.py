#!/usr/bin/python
#
# This is a Hello World example that formats output as fields.
from collections import deque


from bcc import BPF
from bcc.utils import printb
import re
from text2graph import construct_graph
from collections import deque
# define BPF program
prog2 = """
#include <uapi/linux/ptrace.h>
#include <bcc/proto.h>
int syscall__execve(struct pt_regs *ctx,
    const char __user *filename,
    const char __user *const __user *__argv,
    const char __user *const __user *__envp)
{
    bpf_trace_printk("the file name is %s \\n",filename);
    
    return 0 ; 
}
"""
prog1 = """
#include <uapi/linux/ptrace.h>
#include <bcc/proto.h>

int syscall__hello(struct pt_regs *ctx,int  x) {

    bpf_trace_printk("Hello, World! %d  \\n",x);

    
    return 0;
}
"""
queue = deque()
libcFunctions =  [
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

def epsilon_closure(graph, start_vertex):
    closure = set([start_vertex])
    queue = deque([start_vertex])
    
    while queue:
       vertex = queue.popleft()
       if vertex in graph.keys(): 
        for neighbor, label in graph[vertex]:
            if (label not in libcFunctions) and neighbor not in closure:
                closure.add(neighbor)
                queue.append(neighbor)
    
    return closure

# load BPF program
b = BPF(text=prog1)
b.attach_kprobe(event="__x64_sys_hello", fn_name="syscall__hello")
b2 = BPF(text=prog2)
execve_fnname = b.get_syscall_fnname("execve")
b2.attach_kprobe(event=execve_fnname, fn_name="syscall__execve")
# header
print("%-18s %-16s %-6s %s" % ("TIME(s)", "COMM", "PID", "MESSAGE"))

# format output
# while 1:
#     try:
#         (task, pid, cpu, flags, ts, msg) = b2.trace_fields()
#         if task.decode() != 'result' :
#             continue
        # path = f"{        task.decode()}.txt"
        
        # fd = open(path,'r')
        # str = fd.read()
        # print(str)
#         break
#     except ValueError:
#         continue
#     except KeyboardInterrupt:
#         exit()
#     print("The function name of %s in kernel is %s" % ("hello", b.get_syscall_fnname("hello")))    
#     printb(b"%-18.9f %-16s %-6d %s " % (ts, task, pid, msg))
graph = {}
closures = {}
first = True  
while 1:
    str =""
    try:
        (task, pid, cpu, flags, ts, msg) = b.trace_fields()

        msg_str = msg.decode()
        pattern_3 = r'^ex(\d+)$'
        match = re.match(pattern_3, task.decode())
        if match and first: 
            first = False
            number = match.group(1)
            path = f"secure_policy_{number}.dot"
            graph,start = construct_graph(path)
            print(graph)
            for vertex in graph.keys():
              closures[f'{vertex}']=epsilon_closure(graph,vertex)
            print(closures)
            print(closures[f'{start}'])
            for Vertex in closures[f'{start}'] :
               queue.append(Vertex)
            
        # Regex to find first number after "Hello, World!"
        match = re.search(r'Hello, World! (\d+)', msg_str)
        if match :
          arg_value = match.group(1)
          libc = libcFunctions[int(arg_value)-1]
          temp = deque()
          while   queue :
           x = queue.popleft()
           if x in graph.keys() : 
            for node,edge in graph[x] :
             
             if edge == libc :
                 print(edge,libc) 
                 for y in closures[f'{node}'] :     
                   if y not in temp : 
                    temp.append(y)
                 break
          queue = temp     
          print(f"Syscall argument value: {arg_value}")
          print(queue)
            

    except ValueError:
        continue
    except KeyboardInterrupt:
        exit()
    print("The function name of %s in kernel is %s" % ("hello", b.get_syscall_fnname("hello")))    
    print(str)
    printb(b"%-18.9f %-16s %-6d %s " % (ts, task, pid, msg))
