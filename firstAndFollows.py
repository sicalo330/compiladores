class Grammar():
    def __init__(self, nonTerminals: set[str], terminals: set[str], prodRules: set[tuple[str,str]]):
        self.nonTerminals: set[str] = nonTerminals
        self.terminals: set[str] = terminals
        self.prodRules: set[tuple[str,str]] = prodRules

def allNullable(prod: str, nullable: dict[str,bool]) -> bool:
    for c in prod:
        if not nullable[c]:
            return False
    return True

def firstAndFollows(G: Grammar) -> tuple[dict[str, set],dict[str,set],dict[str,bool]]:
    first: dict[str, set] = {}
    follow: dict[str, set] = {}
    nullable: dict[str, bool] = {}
    
    # Inicializaciones

    for c in G.nonTerminals | G.terminals:
        nullable[c] = False # inicializar nullable a todos falsos

        # inicializar first y follow como todos conjuntos facíos
        first[c] = set()
        follow[c] = set()

    #print("DEBUG: ", nullable, first, follow, "\n")
    
    for rule in G.prodRules:
        if rule[1] == "":
            nullable[rule[0]] = True
    
    #print("DEBUG: ", nullable, "\n")

    for t in G.terminals: # el first de todo terminal es sí mismo
        first[t] = set(t)
    
    #print("DEBUG: ", first, "\n")

    # Guardar estados previos
    prevFirst: dict = {}
    prevFollow: dict = {}
    prevNullable: dict = {}

    firstIteration: bool = True
    iterations: int = 0
    k: int = 0

    while firstIteration or (first != prevFirst and follow != prevFollow and nullable != prevNullable):
        iterations += 1
        print("Iteración: ", iterations, '\n')
        firstIteration = False

        prevFirst = first.copy()
        prevFollow = follow.copy()
        prevNullable = nullable.copy()

        print(first, "\n", prevFirst)

        for rule in G.prodRules:
            k = len(rule[1])
            print(rule, k)

            if (k == 0) or allNullable(rule[1], nullable):
                nullable[rule[0]] = True

            for i in range(k):
                print(i)
                if i == 0 or allNullable(rule[1][0:i-1], nullable):
                    print("FIRST[", rule[0], "] U FIRST[", rule[1][i], "]")
                    first[rule[0]] |= first[rule[1][i]]
                    print(first[rule[0]])

                if i == k-1 or allNullable(rule[1][i+1:k], nullable):
                    print("FOLLOW[", rule[1][i], "] U FOLLOW[", rule[0], "]")
                    follow[rule[1][i]] |= follow[rule[0]]
                    print(follow[rule[1][i]])
                    
                for j in range(i+1,k):
                    if i+1 == j or allNullable(rule[1][i+1:j-1], nullable):
                        print("FOLLOW[", rule[1][i], "] U FIRST[", rule[1][j], "]")
                        follow[rule[1][i]] |= first[rule[1][j]]
                        print(follow[rule[1][i]])

        print(first, "\n", prevFirst)
    return first, follow, nullable

def main():
    nt: set[str] = {'X','Y','Z'}
    t: set[str] = {'a','c','d'}
    pr: set[tuple[str,str]] = {('Z',"d"), ('Z',"XYZ"), ('Y',""), ('Y',"c"), ('X',"Y"), ('X',"a")}
    G = Grammar(nt, t, pr)

    result: tuple[dict[str, set],dict[str,set],dict[str,bool]] = firstAndFollows(G)

    print("FIRST: ", result[0], "\n")
    print("FOLLOW: ", result[1], "\n")
    print("nullable: ", result[2])

main()