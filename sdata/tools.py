# -*-coding: utf-8-*-

def col_to_idx(col):
    """covert xls column to index
    :param col .. column, e.g. 'AA'

    :returns index, e.g. 26

    """
    val = lambda i, x: (26**i) * (ord(x.lower()) - ord('a') + 1)
    return sum([val(i, x) for i, x in enumerate(col[::-1])]) - 1

if __name__ == '__main__':
    print(col_to_idx("aB"))