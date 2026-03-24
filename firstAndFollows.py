class Grammar():
    def __init__(self, nonTerminals: set[str], terminals: set[str], prodRules: set[tuple[str,str]]):
        self.nonTerminals: set[str] = nonTerminals
        self.terminals: set[str] = terminals
        self.prodRules: set[tuple[str,str]] = prodRules

def allNullable(prod: str, nullable: dict) -> bool:
    for c in prod:
        if c in nullable.keys():
            if not nullable[c]:
                return False
    return True

def firstAndFollows(G: Grammar) -> tuple[dict,dict,dict]:
    first: dict = {}
    follow: dict = {}
    nullable: dict = {}
    
    # Inicializaciones

    for c in G.nonTerminals | G.terminals:
        nullable[c] = False
        first[c] = {}
        follow[c] = {}
    
    for rule in G.prodRules:
        if rule[1] == "":
            nullable[rule[0]] = True

    for t in G.terminals: # el first de todo terminal es sí mismo
        first[t] = set(t)

    # Guardar estados previos
    prevFirst: dict = None
    prevFollow: dict = None
    prevNullable: dict = None

    firstIteration: bool = True
    k: int = 0

    while firstIteration or (first != prevFirst and follow != prevFollow and nullable != prevNullable):
        firstIteration = False

        prevFirst = first
        prevFollow = follow
        prevNullable = nullable

        for rule in G.prodRules:
            k = len(rule[1])

            if allNullable(rule[1], nullable):
                nullable[rule[0]] = True

            for i in range(k):
                for j in range(i+1,k):
                    if i == 0 or allNullable(rule[1][0:i-1], nullable):
                        first[rule[0]] |= first[rule[1][i]]

                    if i == k or allNullable(rule[1][i+1:k], nullable):
                        follow[rule[1][i+1]] |= follow[rule[0]]
                    
                    if i+1 == j or allNullable(rule[1][i+1:j-1], nullable):
                        follow[rule[1][i]] |= first[rule[1][j]]

    return first, follow, nullable

def main():
    G = Grammar({'X','Y','Z'}, {'a','c','d'}, {('Z',"d"), ('Z',"XYZ"), ('Y',""), ('Y',"c"), ('X',"Y"), ('X',"a")})

    result = firstAndFollows(G)

    print("FIRST: ", result[0], "\n")
    print("FOLLOW: ", result[1], "\n")
    print("nullable: ", result[2])

main()