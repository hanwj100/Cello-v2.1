#!/usr/bin/env python
"""
    [From Cello 2.0]

    plot_SBOL_designs.py

    Plot the design of DNA constructs using SBOL notation.

    Usage:
    ------
    python plot_SBOL_designs.py  -params     PARAM_FILENAME
                                 -parts      PART_FILENAME
                                 -designs    DESIGN_FILENAME
                                [-regulation REG_FILENAME]
                                 -output     OUT_FILENAME
"""

# Set the backend to use (important for headless servers)
import os.path
from argparse import ArgumentParser
import matplotlib.pyplot as plt
import dnaplotlib as dpl
import csv
import getopt
import sys
from contextlib import redirect_stdout, redirect_stderr
import matplotlib
import logging

matplotlib.use('Agg')


# Original script by...
__author__ = 'Thomas E. Gorochowski <tom@chofski.co.uk>, Voigt Lab, MIT\n\
               Bryan Der <bder@mit.edu>, Voigt Lab, MIT'
__license__ = 'MIT'
__version__ = '1.0'


def make_float_if_needed(s):
    """

    :param s:
    :return:
    """
    try:
        float(s)
        return float(s)
    except ValueError:
        return s


def load_plot_parameters(filename):
    """

    :param filename:
    :return:
    """
    plot_params = {}
    param_reader = csv.reader(open(filename, 'r'), delimiter=',')
    # Ignore header
    header = next(param_reader)
    # Process all parameters
    for row in param_reader:
        if len(row) >= 2:
            if row[1] != '':
                plot_params[row[0]] = make_float_if_needed(row[1])
    return plot_params


def load_part_information(filename):
    """

    :param filename:
    :return:
    """
    part_info = {}
    parts_reader = csv.reader(open(filename, 'r'), delimiter=',')
    header = next(parts_reader)
    header_map = {}
    for i in range(len(header)):
        header_map[header[i]] = i
    attrib_keys = [k for k in list(header_map.keys()) if k not in [
        'part_name', 'type']]
    for row in parts_reader:
        # Make the attributes map
        part_attribs_map = {}
        for k in attrib_keys:
            if row[header_map[k]] != '':
                if k == 'color' or k == 'label_color':
                    part_attribs_map[k] = [
                        float(x) for x in row[header_map[k]].split(';')]
                else:
                    part_attribs_map[k] = make_float_if_needed(
                        row[header_map[k]])
        part_name = row[header_map['part_name']]
        part_type = row[header_map['type']]
        part_info[part_name] = [part_name, part_type, part_attribs_map]
    return part_info


def load_dna_designs(filename, part_info, reverse_char='r'):
    """

    :param filename:
    :param part_info:
    :param reverse_char:
    :return:
    """
    dna_designs = {}
    design_reader = csv.reader(open(filename, 'r'), delimiter=',')
    # Ignore header
    header = next(design_reader)
    # Process all parameters
    for row in design_reader:
        if len(row[0]) != '':
            part_list = []
            for i in range(1, len(row)):
                # Handle reverse parts
                fwd = True
                part_name = row[i]
                if len(part_name) != 0:
                    if part_name[0] == reverse_char:
                        part_name = part_name[1:]
                        fwd = False
                    # Store the design
                    part_design = {}
                    cur_part_info = part_info[part_name]
                    part_design['type'] = cur_part_info[1]
                    # needed to add part name for regulation
                    part_design['name'] = part_name
                    # needed to add fwd for regulation
                    part_design['fwd'] = fwd
                    if fwd:
                        part_design['start'] = i
                        part_design['end'] = i + 1
                    else:
                        part_design['end'] = i
                        part_design['start'] = i + 1
                    part_design['opts'] = cur_part_info[2]
                    part_list.append(part_design)
            dna_designs[row[0]] = part_list
    return dna_designs


def load_regulatory_information(filename, part_info, dna_designs):
    """

    :param filename:
    :param part_info:
    :param dna_designs:
    :return:
    """
    regs_info = {}

    reg_reader = csv.reader(open(filename, 'r'), delimiter=',')
    # Ignore header
    header = next(reg_reader)
    header_map = {}
    for i in range(len(header)):
        header_map[header[i]] = i
    attrib_keys = [k for k in list(header_map.keys()) if k not in [
        'from_partname', 'type', 'to_partname']]

    # reg_reader can only be read once?
    rows = []
    for row in reg_reader:
        rows.append(row)

    design_list = sorted(dna_designs.keys())
    num_of_designs = len(design_list)

    # outer loop: for each design
    for i in range(num_of_designs):
        regs_info[i] = []
        design = dna_designs[design_list[i]]

        # middle loop: for each regulation
        for row in rows:

            # opts
            reg_attribs_map = {}
            for k in attrib_keys:
                if row[header_map[k]] != '':
                    if k == 'color':
                        reg_attribs_map[k] = [
                            float(x) for x in row[header_map[k]].split(';')]
                    else:
                        reg_attribs_map[k] = make_float_if_needed(
                            row[header_map[k]])

            # from, type, to
            type = row[header_map['type']]
            from_partname = row[header_map['from_partname']]
            to_partname = row[header_map['to_partname']]
            from_part = None
            to_part = None

            # inner loop: loop through parts to find 'from' and 'to' parts
            for part1 in design:  # loop through once to find the cds
                if part1['name'] == from_partname:
                    start_part = part1
                    for part2 in design:  # loop through again to find the promoter
                        if part2['name'] == to_partname:
                            end_part = part2
                            # found from-to, save regulation arc
                            reg_info = {'from_part': start_part, 'type': row[header_map['type']], 'to_part': end_part,
                                        'opts': reg_attribs_map}
                            regs_info[i].append(reg_info)
    return regs_info


def plot_dna(dna_designs, png_filename, pdf_filename, plot_params, regs_info):
    """

    :param dna_designs:
    :param out_filename:
    :param plot_params:
    :param regs_info:
    """

    # Suppress (useless) console output
    matplotlib_logger = logging.getLogger("matplotlib")
    matplotlib_logger.setLevel(logging.INFO)
    logging.disable(logging.INFO)

    # Create the renderer
    if 'axis_y' not in list(plot_params.keys()):
        plot_params['axis_y'] = 35
    left_pad = 0.0
    right_pad = 0.0
    scale = 1.0
    linewidth = 1.0
    fig_y = 5.0
    fig_x = 5.0
    if 'backbone_pad_left' in list(plot_params.keys()):
        left_pad = plot_params['backbone_pad_left']
    if 'backbone_pad_right' in list(plot_params.keys()):
        right_pad = plot_params['backbone_pad_right']
    if 'scale' in list(plot_params.keys()):
        scale = plot_params['scale']
    if 'linewidth' in list(plot_params.keys()):
        linewidth = plot_params['linewidth']
    if 'fig_y' in list(plot_params.keys()):
        fig_y = plot_params['fig_y']
    if 'fig_x' in list(plot_params.keys()):
        fig_x = plot_params['fig_x']
    dr = dpl.DNARenderer(scale=scale, linewidth=linewidth,
                         backbone_pad_left=left_pad,
                         backbone_pad_right=right_pad)

    # We default to the standard regulation renderers
    reg_renderers = dr.std_reg_renderers()
    # We default to the SBOL part renderers
    part_renderers = dr.SBOL_part_renderers()

    # Create the figure
    fig = plt.figure(figsize=(fig_x, fig_y))

    # Cycle through the designs an plot on individual axes
    design_list = sorted(dna_designs.keys())
    if regs_info is not None:
        regs_list = sorted(regs_info.keys())

    num_of_designs = len(design_list)
    ax_list = []
    max_dna_len = 0.0
    for i in range(num_of_designs):
        # Create axis for the design and plot
        regs = None
        if regs_info is not None:
            regs = regs_info[i]
        design = dna_designs[design_list[i]]

        ax = fig.add_subplot(num_of_designs, 1, i + 1)
        if 'show_title' in list(plot_params.keys()) and plot_params['show_title'] == 'Y':
            ax.set_title(design_list[i], fontsize=8)
        start, end = dr.renderDNA(
            ax, design, part_renderers, regs, reg_renderers)

        dna_len = end - start
        if max_dna_len < dna_len:
            max_dna_len = dna_len
        ax_list.append(ax)

    for i, ax in enumerate(ax_list):
        ax.set_xticks([])
        ax.set_yticks([])
        # Set bounds
        ax.set_xlim([(-0.01 * max_dna_len) - left_pad,
                     max_dna_len + (0.01 * max_dna_len) + right_pad])
        ax.set_ylim([-plot_params['axis_y'], plot_params['axis_y']])
        ax.set_aspect('equal')
        ax.set_axis_off()
        ax.set_title(f'Design Option {i + 1}', fontsize=5, loc='left')

    # Update the size of the figure to fit the constructs drawn
    fig_x_dim = max_dna_len / 70.0
    if fig_x_dim < 1.0:
        fig_x_dim = 1.0
    fig_y_dim = 1.2 * len(ax_list)
    plt.gcf().set_size_inches((fig_x_dim, fig_y_dim))

    # Save the figure
    plt.tight_layout()
    fig.savefig(png_filename, dpi=300)
    fig.savefig(pdf_filename, transparent=True, dpi=300)
    # Clear the plotting cache
    plt.close('all')

    logging.disable(logging.NOTSET)  # Re-enable console output


def is_valid_file(parser, arg):
    """

    :param parser:
    :param arg:
    :return:
    """
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        return open(arg, 'r')  # return an open file handle


def plotter(params, parts, regulation, designs, png_output, pdf_output, reverse_char=""):
    """

    """
    cur_reverse_char = '@r'
    if reverse_char:
        cur_reverse_char = reverse_char
    plot_params = load_plot_parameters(params)
    part_info = load_part_information(parts)
    dna_designs = load_dna_designs(
        designs, part_info, reverse_char=cur_reverse_char)

    regs_info = None
    if regulation:
        regs_info = load_regulatory_information(
            regulation, part_info, dna_designs)

    plot_dna(dna_designs, png_output, pdf_output, plot_params, regs_info)
