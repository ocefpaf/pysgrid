'''
Created on Mar 23, 2015

@author: ayan
'''
from collections import namedtuple

import numpy as np


GridPadding = namedtuple('GridPadding', ['mesh_topology_var',  # the variable containing the padding information
                                         'face_dim',  # the topology attribute
                                         'node_dim',  # node dimension within the topology attribute
                                         'padding'  # padding type for the node dimension
                                         ]
                         )


def pair_arrays(x_array, y_array):
    """
    Given two arrays to equal dimensions,
    pair their values element-wise.
    
    For example given arrays [[1, 2], [3, 4]]
    and [[-1, -2], [-3, -4]], this function will
    return [[[1, -1], [2, -2]], [[3, -3], [4, -4]]].
    
    :param np.array x_array: a numpy array containing "x" coordinates
    :param np.array y_array: a numpy array containing "y" coordinates
    :return: array containing (x, y) arrays
    :rtype: np.array
    
    """
    x_shape = x_array.shape
    paired_array_shape = x_shape + (2,)
    paired_array = np.empty(paired_array_shape, dtype=np.float64)
    paired_array[..., 0] = x_array[:]
    paired_array[..., 1] = y_array[:]
    return paired_array


def check_element_equal(lst):
    """
    Check that all elements in an
    iterable are the same.
    
    :params lst: iterable object to be checked
    :type lst: np.array, list, tuple
    :return: result of element equality check
    :rtype: bool
    
    """
    return lst[1:] == lst[:-1]


def does_intersection_exist(a, b):
    set_a = set(a)
    try:
        set_b = set(b)
    except TypeError:
        intersect_exists = False
    else:
        intersect = set_a.intersection(set_b)
        if len(intersect) > 0:
            intersect_exists = True
        else:
            intersect_exists = False
    return intersect_exists


def determine_variable_slicing(sgrid_obj, nc_variable, method='center'):
    """
    Figure out how to slice a variable. This function
    only knows who to figure out slices that would be
    used to trim data before averaging to grid cell
    centers; grid cell nodes will be supported later.
    
    :param sgrid_obj: an SGrid object derived from a netCDF file or netCDF4.Dataset object
    :type sgrid_obj: sgrid.SGrid
    :param nc_dataset: a netCDF4.Dataset object from which the sgrid_obj was derived
    :type nc_dataset: netCDF4.Dataset
    :param str variable: the name of a variable to be sliced
    :param str method: slice method for analysis at grid cell centers or grid cell nodes; accepts either 'center' or 'node'
    :return: the slice for the varible for the given method
    :rtype: tuple
    
    """
    grid_variables = sgrid_obj.grid_variables
    if grid_variables is None:
        grid_variables = []
    var_dims = nc_variable.dimensions
    node_dims = tuple(sgrid_obj.node_dimensions.split(' '))
    separate_edge_dim_exists = does_intersection_exist(var_dims, node_dims)
    slice_indices = tuple()
    if separate_edge_dim_exists:
        try:
            padding = sgrid_obj.face_padding  # try 2D sgrid
        except AttributeError:
            padding = sgrid_obj.volume_padding  # if not 2D, try 3D sgrid
    else:
        padding = sgrid_obj.all_padding()
    if method == 'center':
        for var_dim in var_dims:
            try:
                padding_info = next((info for info in padding if info.face_dim == var_dim))
            except StopIteration:
                slice_index = np.s_[:]
                slice_indices += (slice_index,)
            else:
                padding_val = padding_info[-1]
                slice_datum = sgrid_obj.padding_slices[padding_val]
                lower_slice, upper_slice = slice_datum
                slice_index = np.s_[lower_slice:upper_slice]
                slice_indices += (slice_index, )
    else:
        pass
    return slice_indices


def infer_avg_axes(sgrid_obj, nc_var_obj):
    """
    Infer which numpy axis to average over given
    the a variable defined on the grid. Works
    well for 2D. Not so sure about 3D.
    
    """
    var_dims = nc_var_obj.dimensions
    node_dimensions = tuple(sgrid_obj.node_dimensions.split(' '))
    separate_edge_dim_exists = does_intersection_exist(node_dimensions, var_dims)
    if separate_edge_dim_exists:
        padding = sgrid_obj.get_all_face_padding()
    else:
        padding = sgrid_obj.get_all_face_padding() + sgrid_obj.get_all_edge_padding()
    # define center averaging axis for a variable
    for var_dim in var_dims:
        try:
            padding_info = next((info for info in padding if info.face_dim == var_dim))
        except StopIteration:
            padding_info = None
            avg_dim = None
            continue
        else:
            avg_dim = var_dim  # name of the dimension we're averaging over
            break  # exit the loop once it's found
    if padding_info is not None and avg_dim is not None:
        var_position = var_dims.index(avg_dim)
        center_avg_axis = len(var_dims) - var_position - 1
    else:
        center_avg_axis = None
    # define the node averaging axis for a variable
    if center_avg_axis == 1:
        node_avg_axis = 0
    elif center_avg_axis == 0:
        node_avg_axis = 1
    else:
        node_avg_axis = None
    return center_avg_axis, node_avg_axis


def calculate_bearing(lon_lat_1, lon_lat_2):
    """
    return bearing from true north in degrees
    
    """
    lon_lat_1_radians = lon_lat_1 * np.pi/180
    lon_lat_2_radians = lon_lat_2 * np.pi/180
    lon_1 = lon_lat_1_radians[..., 0]
    lat_1 = lon_lat_1_radians[..., 1]
    lon_2 = lon_lat_2_radians[..., 0]
    lat_2 = lon_lat_2_radians[..., 1]
    print(lon_1.shape)
    arg_1 = np.sin(lon_2-lon_1) * np.cos(lat_2)
    print(arg_1.shape)
    arg_2 = np.cos(lat_1)*np.sin(lat_2) - np.sin(lat_1)*np.cos(lat_2)*np.cos(lon_2-lon_1)
    print(arg_2.shape)
    bearing_radians = np.arctan2(arg_1, arg_2)
    print(bearing_radians.shape)
    bearing_degrees = bearing_radians * 180/np.pi
    print('Bearing degress shape: {0}'.format(bearing_degrees.shape))
    return (bearing_degrees + 360) % 360


def calculate_angle_from_true_east(lon_lat_1, lon_lat_2):
    bearing = calculate_bearing(lon_lat_1, lon_lat_2)
    print('Bearing shape: {0}'.format(bearing.shape))
    bearing_from_true_east = 90 - bearing
    bearing_from_true_east_radians = bearing_from_true_east * np.pi/180
    print('Bearing radians shape: {0}'.format(bearing_from_true_east_radians.shape))
    # not sure if this is the most appropriate thing to do for the last grid cell
    angles = np.append(bearing_from_true_east_radians, bearing_from_true_east_radians[-1], axis=-1)
    return angles
    