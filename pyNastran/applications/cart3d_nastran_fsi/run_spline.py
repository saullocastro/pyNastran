from __future__ import print_function
import os
import sys

from six import iteritems
from numpy import pi, zeros, matrix, searchsorted #, float64, memmap
from numpy import log as natural_log
from numpy.linalg import inv

from pyNastran.bdf.bdf import BDF
from pyNastran.op2.op2 import OP2
#from pyNastran.f06.f06 import F06
from pyNastran.converters.cart3d.cart3d import Cart3D
#from pyNastran.applications.cart3d_nastran_fsi.math_functions import print_matrix

from pyNastran.utils.log import get_logger
debug = True
log = get_logger(None, 'debug' if debug else 'info')


def read_op2(op2_filename, isubcase=1):
    """"""
    log.info('---starting deflectionReader.init of %s---' % op2_filename)
    op2 = OP2()
    op2.set_subcases(subcases=[isubcase])
    op2.set_results('displacements')
    op2.read_op2(op2_filename)
    displacment_obj = op2.displacements[isubcase]
    log.info('---finished deflectionReader.init of %s---' % op2_filename)
    return displacment_obj


#def read_f06(f06_filename, isubcase=1):
    #log.info('---starting deflectionReader.init of %s---' % f06_filename)
    #f06 = F06()
    #terms = ['force', 'stress', 'stress_comp', 'strain', 'strain_comp',
             #'displacement', 'grid_point_forces']
    #f06.set_results('displacements')
    #f06.read_f06(f06_filename)
    #displacment_obj = f06.displacements[isubcase]

    ##op2.nastranModel.printDisplacement()
    ##displacements = convertDisplacements(displacements)
    #log.info('---finished deflectionReader.init of %s---' % f06_filename)
    #return displacment_obj.translations


def read_half_cart3d_points(cfd_grid_file):
    """return half model points to shrink xK matrix"""
    cart = Cart3D()
    cart.read_cart3d(cfd_grid_file)
    points, elements, regions, loads = cart.make_half_model()
    return points


def write_new_cart3d_mesh(cfd_grid_file, cfd_grid_file2, wA):
    """takes in half model wA, and baseline cart3d model, updates full model grids"""
    log.info("---starting write_new_cart3d_mesh---")

    # make half model
    cart = Cart3D()
    result_names = ['Cp']
    cart.read_cart3d(cfd_grid_file, result_names=result_names) # reading full model
    points, elements, regions, loads = cart.make_half_model()

    # adjusting points
    points2 = {}
    for (ipoint, point) in sorted(iteritems(points)):
        wai = wA[ipoint]
        (x, y, z) = point
        points2[ipoint] = [x, y, z + wai]

    # mirroring model
    points, elements, regions, loads = cart.make_mirror_model(points2, elements, regions, loads)

    # writing half model; no loads (cleans up leftover parameters)
    cart.write_cart3d(cfd_grid_file, points, elements, regions)

    log.info("---finished write_new_cart3d_mesh---")
    sys.stdout.flush()


def remove_duplicate_nodes(node_list, mesh):
    """
    Removes nodes that have the same (x,y) coordinate.
    Note that if 2 nodes with different z values are found, only 1 is returned.
    This is intentional.
    """
    node_list.sort()
    log.info("node_list_a = %s" % node_list)
    node_dict = {}
    for inode in node_list:
        x, y, z = mesh.Node(inode).get_position()
        node_dict[(x, y)] = inode
    node_list = node_dict.values()
    node_list.sort()
    log.info("node_list_b = %s" % node_list)
    sys.stdout.flush()
    return node_list

def run_map_deflections(node_list, bdf_filename, out_filename, cart3d, cart3d2, log=None):
    fbase, ext = os.path.splitext(out_filename)
    if ext == '.op2':
        deflections = read_op2(out_filename)
    #elif ext == '.f06':
        #deflections = read_f06(out_filename)
    else:
        raise NotImplementedError('out_filename = %r' % out_filename)

    mesh = BDF(debug=True, log=log)
    mesh.read_bdf(bdf_filename, xref=True, punch=False)

    node_list = remove_duplicate_nodes(node_list, mesh)
    C = getC_matrix(node_list, mesh)
    wS = get_WS(node_list, deflections)
    del deflections

    aero_points = read_half_cart3d_points(cart3d)
    wA = get_WA(node_list, C, wS, mesh, aero_points)
    del C
    del mesh

    write_new_cart3d_mesh(cart3d, cart3d2, wA)
    return (wA, wS)

def get_WA(node_list, C, wS, mesh, aero_points):
    log.info('---starting get_WA---')
    #print print_matrix(C)

    C = inv(C) * wS  # Cws matrix, P matrix
    #P = solve(C, wS)
    #C*P=wS
    #P = C^-1*wS

    wA = getXK_matrix(C, node_list, mesh, aero_points)
    #wA = xK*C*wS
    log.info('---finished get_WA---')
    sys.stdout.flush()
    return wA

def getXK_matrix(Cws, node_list, mesh, aero_points):
    log.info('---starting getXK_matrix---')
    D = 1.
    piD16 = pi * D * 16.

    nnodes = len(node_list)
    #nPoints = len(aero_points.keys())
    wa = {}
    #i = 0
    for iaero, aero_node in sorted(iteritems(aero_points)):
        xK = zeros(nnodes+3, 'd')
        #nodeI = mesh.Node(iNode)

        xa, ya, za = aero_node

        xK[0] = 1.
        xK[1] = xa
        xK[2] = ya

        j = 3
        for jnode in node_list:
            structural_node = mesh.Node(jnode)
            (xs, ys, zs) = structural_node.get_position()

            Rij2 = (xa-xs)**2. + (ya-ys)**2  # Rij^2
            if Rij2 == 0.:
                xK[j] = 0.
            else:
                Kij = Rij2 * natural_log(Rij2) / piD16
                xK[j] = Kij
            j += 1

        wai = xK * Cws
        wa[iaero] = wai[0, 0]
        #print("w[%s]=%s" % (iaero, wi[0, 0]))
        #i += 1
    #print('---wa---')
    #print('wa = ', wa)
    log.info('---finished getXK_matrix---')
    sys.stdout.flush()
    return wa

def get_WS(node_list, deflections):
    log.info('---staring get_WS---')
    nnodes = len(node_list)
    Wcolumn = matrix(zeros((3 + nnodes, 1), 'd'))
    i = 3
    nodes = deflections.node_grid[:, 0]
    for inode in node_list:
        inodei = searchsorted(nodes, inode)
        dx, dy, dz = deflections.data[0, inodei, :2] #deflections[inode]
        Wcolumn[i] = dz
        log.info("wS[%s=%s]=%s" % (inode, i, dz))
        i += 1
    print(max(Wcolumn))
    log.info('---finished get_WS---')
    sys.stdout.flush()

    wSmax = max(Wcolumn)
    print("wSmax = %s" % wSmax[0, 0])
    return Wcolumn

def getC_matrix(node_list, mesh):
    log.info('---starting getCmatrix---')
    D = 1.
    piD16 = pi * D * 16.

    nnodes = len(node_list)
    i = 3
    #C = memmap('Cmatrix.map', dtype='float64', mode='write', shape=(3+nnodes, 3+nnodes) )
    log.info('nnodes=%s' % nnodes)
    sys.stdout.flush()
    C = matrix(zeros((3 + nnodes, 3 + nnodes), 'float64'))
    for inode in node_list:
        nodeI = mesh.Node(inode)
        #i = inode+3
        (xi, yi, zi) = nodeI.get_position()
        #x,y,z = p

        C[0, i] = 1.
        C[1, i] = xi
        C[2, i] = yi

        C[i, 0] = 1.
        C[i, 1] = xi
        C[i, 2] = yi

        j = 3
        for jnode in node_list:
            #j = 3+jnode
            nodeJ = mesh.Node(jnode)
            xj, yj, zj = nodeJ.get_position()
            if i == j:
                C[i, j] = 0.
            else:
                Rij2 = (xi-xj)**2. + (yi-yj)**2  # Rij^2
                if Rij2 == 0.:
                    C[i, j] = 0.
                else:
                    Kij = Rij2 * natural_log(Rij2) / piD16
                    C[i, j] = Kij
                    #msg = "i=%s j=%s xi=%s xj=%s yi=%s yj=%s Rij2=%s Kij=%s" %(
                        #i, j, xi, xj, yi, yj, Rij2, Kij)
                    #assert isinstance(Kij,float64), msg
            j += 1
        i += 1
    log.info('---finished getCmatrix---')
    sys.stdout.flush()
    return C


def main(): # pragma: no cover
    basepath = os.getcwd()
    configpath = os.path.join(basepath, 'inputs')
    workpath = os.path.join(basepath, 'outputsFinal')

    bdf_filename = os.path.join(configpath, 'fem3.bdf')
    #f06_filename = os.path.join(configpath, 'fem3.f06')
    op2_filename = os.path.join(workpath, 'fem3.op2')
    cart3d = os.path.join(configpath, 'Cart3d_bwb.i.tri')
    node_list = [
        20037, 21140, 21787, 21028, 1151, 1886, 2018, 1477, 1023, 1116, 1201,
        1116, 1201, 1828, 2589, 1373, 1315, 1571, 1507, 1532, 1317, 1327, 2011,
        1445, 2352, 1564, 1878, 1402, 1196, 1234, 1252, 1679, 1926, 1274, 2060,
        2365, 21486, 20018, 20890, 20035, 1393, 2350, 1487, 1530, 1698, 1782,
    ]
    #node_list = [1001, 1002, 1003, 1004, 1005, 1006]  # these are the hard points
    #node_list = mesh.getNodeIDs() # [0:200]
    cart3d2 = cart3d + '_deflected'

    wA, wS = run_map_deflections(node_list, bdf_filename, op2_filename, cart3d, cart3d2, log=log)
    print("wAero = %s" % wA)
    wSmax = max(wS)
    print("wSmax = %s" % wSmax[0, 0])


if __name__ == '__main__': # pragma: no cover
    main()
