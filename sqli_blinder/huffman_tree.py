
def huffman_tree(stats):

    total = sum([stats[k] for k in stats])
    data = [(ch,stats[ch]*1./total) for ch in stats]

    #data_sorted = np.sort(data)[::-1]
    #data_sorted = sorted(data)[::-1]
    data_sorted = sorted(data,key=lambda x: x[1])[::-1]
    struct = [(x,x) for x in data_sorted]

    while True:        
        a2=struct.pop()
        a1=struct.pop()
        new_val = a1[0][1]+a2[0][1]
        new_tree = (a1[1],a2[1])
        for i in range(len(struct)):
            if struct[i][0][1]<new_val:
                break
        struct.insert(i,(('temp',new_val),new_tree))
        if len(struct)==1:
            break

    return struct[0][1]

def score(tree):
    return score_inner(1,tree)

def score_inner(turn,tree):
    res = 0.
    subtrees = [tree[0],tree[1]]
    for subtree in subtrees:
        
        if type(subtree[1])==float:
            res += turn*subtree[1]
        else:
            res += score_inner(turn+1,subtree)
    return res

def get_chars_in_tree(tree):
    if type(tree[1])==float:
        return [tree[0]]
    res = []
    subtrees = [tree[0],tree[1]]
    for subtree in subtrees:        
        if type(subtree[1])==float:
            res.append(subtree[0])
        else:
            res+=get_chars_in_tree(subtree)
    return res
    
    