#!/usr/bin/evn python

import sys, argparse
from itertools import chain

get_range = lambda x: [min(chain.from_iterable(x)), max(chain.from_iterable(x))]

def build_dict(infile):
    """
    The data structure of alignment coordinates is dictionary.
    This function is to build the dictionary.
    Argument: infile: input file, should be output from mummer delta-filter.
    """

    coords = {}
    sizes = {}

    for line in infile:
        fields = line.split()
        ref_st, ref_end, qry_st, qry_end = map(int, fields[0:4])
        qry_chr, qry_size = fields[14], int(fields[8])
        if qry_chr not in coords:
            coords[qry_chr] = {0:[], 1:[]} # 0=ref; 1=qry
            sizes[qry_chr] = qry_size
        coords[qry_chr][0].append([ref_st, ref_end])
        coords[qry_chr][1].append(sorted([qry_st, qry_end]))
        
    return coords, sizes

def get_parser():
    """ Parse command line. """
    
    desc = "Very aggressive clustering of homologous regions based on mummer coords file"
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('coords', type=argparse.FileType('rU'), help="mummer show-coords output")
    parser.add_argument('ref', type=str, help="reference chromosome")
    parser.add_argument('-d', '--dist', type=int, default=15000, help="maximal distance for clustering")
    parser.add_argument('-o', '--output', type=str, default=sys.stdout, help="output file, default stdout")
    return parser

def get_gaps( rows ):
    """
    Calculate gap size between two adjacent alignment blocks.
    Argument: rows - list of coordinates of alignment blocks.
    """

    n = len(rows) - 1
    gaps = [ rows[i+1][0]-rows[i][1] for i in range(n) ]
    return gaps

def get_block_size( coords ):
    """
    Calculate the size of alignment blocks.
    Argument: coords - list of coordinates of alignment blocks.
    """
    return [ x[1]-x[0] for x in coords ]

def _scan_reverse(gaps, center, dist):
    """
    Scan along reference sequences (starting at the largest alignment block, or the center block), and check whether two adjacent alignment blocks are farther than a given distance. Once two blocks are farther apart, then stop scanning.
    Arguments:
        gaps - list of gap size between adjacent alignment blocks
        center - the index of largest alignment blocks
        dist - distance
    """

    for i in range( 0, center ):
        idx_gap = center - 1 - i
        gap = gaps[idx_gap]
        if gap >= dist: return idx_gap+1
    return 0

def _scan_forward( gaps, center, dist ):
    """
    Scan along reference sequences (starting at the largest alignment block, or the center block), and check whether two adjacent alignment blocks are farther than a given distance. Once two blocks are farther apart, then stop scanning.
    Arguments:
        gaps - list of gap size between adjacent alignment blocks
        center - the index of largest alignment blocks
        dist - distance
    """

    n = len(gaps)
    for i in range( center, n ):
        idx_gap = i
        gap = gaps[idx_gap]
        if gap >= dist: return idx_gap+1
    return n+1
    
def scan( gaps, center, dist ):
    """
    Determine the number of alignment blocks that can be "merged" into the final "giant" block given the defined distance threshold.
    Arguments:
        gaps - list of gap size between adjacent alignment blocks
        center - the index of largest alignment blocks
        dist - distance
    """
    return _scan_reverse( gaps, center, dist ), _scan_forward( gaps, center, dist )

def cluster_regions( coords, dist ):
    """
    Merge alignment blocks into a giant block if the distance between adjacent original blocks is smaller than dist threshold.
    Arguments:
        coords -  list of coordinates of alignment blocks
        dist - distance threshold
    """

    gaps = get_gaps( coords )
    blocks = get_block_size( coords )

    max_block = max( blocks )
    center = blocks.index(max_block)

    stblock, endblock = scan( gaps, center, dist )
    return get_range( coords[stblock:endblock] )

def clustering( rcoords, qcoords, length, dist ):
    """
    For each query chromosome and matching reference chromosome, cluster alignment blocks if their distance is no greater than dist threshold.
    Arguments:
        rcoords - list of coordinates of alignment blocks in reference
        qcoords - list of coordinates of alignment blocks in query
        length - size of query sequences
        dist - distance threshold
    """

    # add an interative routine to be more aggressive on larger regions
    newqsize = 0
    while True:
        refst, refend = cluster_regions( rcoords, dist )
        qryst, qryend = cluster_regions( qcoords, dist )
        qsize = qryend - qryst
        if qsize/length >= 0.95 or qsize == newqsize:
            return refst, refend, qryst, qryend
        else:
            dist = 2*dist
            newqsize = qsize

def _processing( infile, rchr, dist, outf ):
    """
    For each reference chromosome, group alignment blocks from each possible query chromosomes.
    Arguments:
        infile - input file, the output from mummer delta-filter command
        rchr - reference chromosome
        dist - distance threshold
        outf - output file
    """

    coords, sizes = build_dict(infile)
    qry_chrs = list(coords.keys())

    print("Primary\tHaplotig\tPrimary_Start\tPrimary_end\tHaplotig_Start\tHaplotig_End\tHaplotig_Length", file=outf)
    for qchr in qry_chrs:
        refcoords = coords[qchr][0]
        qrycoords = coords[qchr][1]
        refst, refend, qryst, qryend = \
            clustering( refcoords, sorted(qrycoords), sizes[qchr], dist )

        print("%s\t%s\t%d\t%d\t%d\t%d\t%d" % \
            (rchr, qchr, refst, refend, qryst, qryend, sizes[qchr]), file=outf)

def main():

    parser = get_parser()
    args = parser.parse_args()
    infile = args.coords
    rchr = args.ref
    dist = args.dist
    outf = args.output
    print("Cluster homologous regions that are within %d bp." % dist, file=sys.stderr)

    _processing( infile, rchr, dist, outf )

if __name__=="__main__":
    main()
