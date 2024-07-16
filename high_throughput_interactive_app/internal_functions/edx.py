"""
Functions used in EDX interactive plot using dash module to detach it completely from Jupyter Notebooks.
Internal use for Institut Néel and within the MaMMoS project, to export and read big datasets produced at Institut Néel.

@Author: William Rigaut - Institut Néel (william.rigaut@neel.cnrs.fr)
"""

import pathlib
import numpy as np
import plotly.graph_objects as go
import xml.etree.ElementTree as ET
from openpyxl import load_workbook


def generate_spectra(foldername, x_pos, y_pos):
    """Reading the EDX data from .xml datafile exported by the BRUKER software. The function will iter through the file,
    fetching the needed attributs in the metadata and the actual data to create a Scatter Figure with the plotly module

    Parameters
    ----------
    foldername : STR
        Folder that contains all the EDX datafiles in the .xml format.
        Used to read data in the correct path
    x_pos, ypos : INT, INT
        Horizontal position X (in mm) and vertical position Y (in mm) on the sample.
        The EDX scan saved the datafiles labeled by two numbers (a, b) corresponding to the scan number in the x and y positions.

    Returns
    -------
    fig : FIGURE OBJ
        Figure object from plotly.graph_objects containing a Scatter plot
    """
    # Defining a dummy Figure object to send when certains conditions are not met
    empty_fig = go.Figure(data=go.Scatter())
    empty_fig.update_layout(height=700, width=1300)
    # Converting wafer position to datafile label number
    start_x, start_y = -40, -40
    step = 5
    x_idx, y_idx = int((x_pos - start_x) / step + 1), int((y_pos - start_y) / step + 1)

    # If the user did not select a data folder, the displayed graph will be empty
    if foldername is None:
        return empty_fig

    filepath = pathlib.Path(f"./data/EDX/{foldername}/Spectrum_({x_idx},{y_idx}).spx")

    # Metadata to keep for displaying quantification results
    params = [
        "Atom",
        "XLine",
        "AtomPercent",
        "MassPercent",
        "NetIntens",
        "Background",
        "Sigma",
    ]
    voltage = 0
    energy_step = 0.0
    zero_energy = 0.0
    results_ext = []
    element_list = []

    # Iteration through the XML datafile, searching for important metadata and EDX spectra
    tree = ET.parse(filepath)
    root = tree.getroot()
    for elm in root.iter():
        if elm.tag == "PrimaryEnergy":
            voltage = int(float(elm.text))
        elif elm.tag == "WorkingDistance":
            working_distance = float(elm.text)
        elif elm.tag == "CalibLin":
            energy_step = float(elm.text)
        elif elm.tag == "CalibAbs":
            zero_energy = float(elm.text)
        elif elm.tag == "Channels":
            edx_spectra = np.array(
                [
                    ((i + 1) * energy_step + zero_energy, int(counts))
                    for i, counts in enumerate(elm.text.split(","))
                ]
            )
        elif elm.tag == "ClassInstance" and elm.get("Name") == "Results":
            for child in elm.iter():
                if child.tag == "Result":
                    results_ext.append([])
                elif child.tag in params:
                    if child.tag == "Atom" and int(child.text) < 10:
                        results_ext[-1].append((child.tag, f"0{child.text}"))
                    else:
                        results_ext[-1].append((child.tag, child.text))
                elif child.tag == "ExtResults":
                    break
        elif elm.tag == "ClassInstance" and elm.get("Name") == "Elements":
            for child in elm.iter():
                if child.get("Type") == "TRTPSEElement":
                    name_elm = child.get("Name")
                    for nb in child.iter():
                        if nb.tag == "Element":
                            nb_elm = nb.text
                    element_list.append([int(nb_elm), name_elm])

    # Creating the scatter plot with plotly.graph_objects library and updating title
    fig = go.Figure(
        data=[
            go.Scatter(
                x=[elm[0] for elm in edx_spectra],
                y=[elm[1] for elm in edx_spectra],
                marker_color="purple",
            )
        ]
    )
    fig.update_layout(
        title=f"EDX Spectrum for {foldername} at position ({x_pos}, {y_pos})"
    )

    return fig


def get_elements(foldername, with_plot=False):
    """Reading from the Global Spectrum Results.xlsx file, the function will return all the element that were used for the quantification
    but excluding the element that were deconvoluted

    Parameters
    ----------
    foldername : STR
        Folder that contains all the EDX datafiles in the .xml format.
        Used to read data in the correct path
    with_plot : BOOL (optional)
        False by default, if True, the function will also return another LIST containing the data after reading the .xlsx file

    Returns
    -------
    elm_options : LIST
        List of element that were used for the quantification
    LIST_DATA : LIST (optional)
        List containing the data read inside the .xlsx file
    """

    # Reading in .xlsx file using openpyxl library, checking if file exists, if not returns empty list
    filepath = pathlib.Path(f"./data/EDX/{foldername}/Global spectrum results.xlsx")
    try:
        wb = load_workbook(filename=filepath)
    except FileNotFoundError:
        return []
    ws = wb.active

    # putting all the data inside lists to obtain a treatable format
    LIST_DATA = []
    for i, row in enumerate(ws.values):
        LIST_DATA.append(row)

    # checking all the element that have been quantified by excluding the deconvoluted ones
    index_tab = []
    for index, elm in enumerate(LIST_DATA[-3]):
        if index > 0 and elm is not None:
            if float(elm) != 0.0:
                index_tab.append(index)
    elm_options = [LIST_DATA[0][index] for index in index_tab]

    if with_plot:
        return elm_options, LIST_DATA
    else:
        return elm_options


def generate_heatmap(folderpath_edx, element_edx):
    """Plotting results from element quantification inside the Global Spectrum Results.xlsx file

    Parameters
    ----------
    folderpath_edx : STR
        Folder that contains the Global Spectrum Results.xlsx file to read quantification results
        Used to read data in the correct path
    element_edx : STR
        Element to display the concentration in at% from the xlsx file as a function of (X, Y) positions

    Returns
    -------
    fig : FIGURE OBJ
        Figure object from plotly.graph_objects containing a Heatmap plot
    """
    # Defining a dummy Figure object to send when certains conditions are not met
    empty_fig = go.Figure(data=go.Heatmap())
    empty_fig.update_layout(height=800, width=800)
    if folderpath_edx is None or element_edx is None:
        return empty_fig

    # Get the data from the .xlsx file
    elms, LIST_DATA = get_elements(folderpath_edx, with_plot=True)
    if element_edx not in elms:
        return empty_fig

    step_x = 5
    step_y = 5
    start_x = -40
    start_y = -40
    X_POS = []
    Y_POS = []
    ELM = []

    for row in LIST_DATA:
        if row[0] == "Spectrum":
            index = row.index(element_edx)
        elif row[0].startswith("Spectrum_"):
            x_index, y_index = row[0].split("(")[-1].split(")")[0].split(",")
            x_pos, y_pos = (int(x_index) - 1) * step_x + start_x, (
                int(y_index) - 1
            ) * step_y + start_y
            if np.abs(x_pos) + np.abs(y_pos) <= 60:
                X_POS.append(x_pos)
                Y_POS.append(y_pos)
                ELM.append(float(row[index]))

    fig = go.Figure(data=go.Heatmap(x=X_POS, y=Y_POS, z=ELM, colorscale="Jet"))
    fig.update_layout(title=f"EDX Heatmap for element {element_edx}")

    return fig
