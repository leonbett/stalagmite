import subprocess
import json
import re

from parser_info import parser_functions, parser_entry_point


def run(cmd):
    subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='replace')

def main():
    # not doing "make clean" to avoid deleting jsons/ etc.
    run("make")
    run("opt -dot-callgraph combined.bc")

    with open("combined.bc.callgraph.dot", "r") as f:
        lines = f.readlines()

    flat_parser_functions = [item for sublist in parser_functions.values() for item in sublist]
    
    d = {} # maps `parser function name` to `node name`
    reverse_d = {}
    pattern_node = r'\s*(Node0x.+?) \[shape=record,label="{(.+?)}"\];'
    for line in lines:
        m = re.match(pattern_node, line)
        if m:
            node = m.group(1)
            fname = m.group(2)
            if fname in flat_parser_functions:
                d[fname] = node
                reverse_d[node] = fname

    print(json.dumps(d, indent=1))

    graph = {} # maps node to node

    pattern_edge = r'\s*(Node0x.+) -> (Node0x.+);'
    for line in lines:
        m = re.match(pattern_edge, line)
        if m:
            src = m.group(1)
            dst = m.group(2)
            # check that src, dst are both parser functions
            if src in d.values() and dst in d.values():
                if dst not in graph:
                    graph[dst] = []
                if src not in graph:
                    graph[src] = []
                graph[src].append(dst)

    print(json.dumps(graph, indent=1))
    print("nodes in graph: ", len(graph.keys()))

    horizontal = False # True
    dotg = []
    dotg.append('digraph "Call graph" {')
    if horizontal: dotg.append('   rankdir=LR;')
    #dotg.append('   label="Call graph";')
    dotg.append('   Q [style=invis, width=0, height=0];')

    for src, dsts in graph.items():
        if reverse_d[src] == parser_entry_point[1]:
            #constraint=false => will be at top
            dotg.append(f'  {src} [constraint=false,shape=record,label="{{{reverse_d[src]}}}"];')
            # dotg.append(f'Q -> {src} [label="entry"];') # invis dummy
            dotg.append(f'Q -> {src} [label=" "];') # invis dummy

        else:
            dotg.append(f'  {src} [shape=record,label="{{{reverse_d[src]}}}"];')
        for dst in dsts:
            dotg.append(f'  {src} -> {dst};')
    dotg.append('}')

    with open("final_cg.dot", "w") as f:
        f.writelines(dotg)

    run("dot -Tpdf -Gmargin=0 final_cg.dot -o cg.pdf")

    print("done")


if __name__ == "__main__":
    main()
