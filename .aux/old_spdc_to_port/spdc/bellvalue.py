# Code by Ilija Funk, last edited 13.06.2024, version 0.1
# This module contains functions for calculating the Bell value.
# Needs os, numpy, matplotlib.

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm


def calc_e_s(matrix):

    matrix[matrix == 0] = 1e-20

    E1 = ((matrix[0][0] + matrix[1][1]) - (matrix[0][1] + matrix[1][0])) / (
        (matrix[0][0] + matrix[1][1]) + (matrix[0][1] + matrix[1][0])
    )
    E2 = (
        (matrix[0][0 + 2] + matrix[1][1 + 2]) - (matrix[0][1 + 2] + matrix[1][0 + 2])
    ) / ((matrix[0][0 + 2] + matrix[1][1 + 2]) + (matrix[0][1 + 2] + matrix[1][0 + 2]))
    E3 = (
        (matrix[0 + 2][0] + matrix[1 + 2][1]) - (matrix[0 + 2][1] + matrix[1 + 2][0])
    ) / ((matrix[0 + 2][0] + matrix[1 + 2][1]) + (matrix[0 + 2][1] + matrix[1 + 2][0]))
    E4 = (
        (matrix[0 + 2][0 + 2] + matrix[1 + 2][1 + 2])
        - (matrix[0 + 2][1 + 2] + matrix[1 + 2][0 + 2])
    ) / (
        (matrix[0 + 2][0 + 2] + matrix[1 + 2][1 + 2])
        + (matrix[0 + 2][1 + 2] + matrix[1 + 2][0 + 2])
    )

    E = np.round([E1, E2, E3, E4], 2)
    S = np.round(
        [-E1 + E2 + E3 + E4, E1 - E2 + E3 + E4, E1 + E2 - E3 + E4, E1 + E2 + E3 - E4], 2
    )
    return E, S


def plot(data, B_detector_angles, folder_path, file_number, bell_value=True):
    """
    data:			4x16 numpy array of visibility curves counts in the order V-H-D-A
    bell_value:		True or False; adds a list of the calculated Bell values and a table with the Bell measurement values
    """
    # improve visualisation by repeating the zero degree data at the end of the plot
    first_column = data[:, 0]
    matrix_for_plot = np.hstack((data, first_column.reshape(-1, 1)))
    B_detector_angles_for_plot = np.append(B_detector_angles, [360])

    # Set global font properties
    plt.rcParams["font.size"] = 12
    plt.rcParams["font.family"] = "Gill Sans MT"
    plt.rcParams["font.style"] = "normal"

    plt.switch_backend("Agg")

    plt.plot(B_detector_angles_for_plot, matrix_for_plot[0, :], label="V")
    plt.plot(B_detector_angles_for_plot, matrix_for_plot[2, :], label="H")
    plt.plot(B_detector_angles_for_plot, matrix_for_plot[1, :], label="D")
    plt.plot(B_detector_angles_for_plot, matrix_for_plot[3, :], label="A")

    plt.gcf().set_size_inches(10, 6)
    plt.xlabel("Angle Bob", fontsize=20)
    plt.ylabel("Coincidences", fontsize=20)
    plt.legend(prop={"size": 12}, title="Angle Alice", loc="upper right")
    plt.grid()
    plt.xlim(0, 360)
    plt.ylim(bottom=0)
    plt.tick_params(axis="both", which="major", labelsize=18)
    plt.xticks(np.arange(0, 361, 22.5), fontsize=10)
    # plt.yticks(np.arange(0, 1000, 200), fontsize=17)

    if bell_value == True:
        # generate coincidence matrix
        bell_angles_for_bob = [22.5, 67.5, 112.5, 157.5]
        bell_angles_for_bob_indices = [
            B_detector_angles.index(angle) for angle in bell_angles_for_bob
        ]
        coincidence_matrix = data[:, bell_angles_for_bob_indices]
        coincidence_matrix[1], coincidence_matrix[2] = (
            coincidence_matrix[2].copy(),
            coincidence_matrix[1].copy(),
        )
        coincidence_matrix[:, 1], coincidence_matrix[:, 2] = (
            coincidence_matrix[:, 2].copy(),
            coincidence_matrix[:, 1].copy(),
        )
        print(coincidence_matrix)

        # calculate Bell value
        E, S = calc_e_s(coincidence_matrix)

        # Define colormap
        colormap = plt.colormaps.get_cmap("coolwarm")

        # Normalize the values in the matrix to range [0, 1]
        normalized_matrix = (coincidence_matrix - np.min(coincidence_matrix)) / (
            np.max(coincidence_matrix) - np.min(coincidence_matrix)
        )

        # Generate colors based on colormap and normalized values
        cell_colors = [[colormap(value) for value in row] for row in normalized_matrix]

        # Display matrix in tabular format below the plot
        coincidence_table = plt.table(
            cellText=coincidence_matrix,
            cellColours=cell_colors,
            rowLabels=["V", "H", "D", "A"],
            colLabels=["22.5°", "112.5°", "67.5°", "157.5°"],
            loc="bottom",
            cellLoc="center",
            bbox=[0, -0.5, 0.4, 0.35],
        )

        label_fontsize = 15
        value_fontsize = 15
        y_offset = -0.22
        y_spacing = 0.08
        x_offset = 0.55
        e_x_label_position = x_offset
        e_x_value_position = 0.05 + x_offset
        s_x_label_position = 0.15 + x_offset
        s_x_value_position = 0.29 + x_offset

        plt.text(
            e_x_label_position,
            y_offset,
            "E1:",
            fontsize=label_fontsize,
            weight="bold",
            transform=plt.gca().transAxes,
        )
        plt.text(
            e_x_value_position,
            y_offset,
            E[0],
            fontsize=value_fontsize,
            transform=plt.gca().transAxes,
        )
        plt.text(
            e_x_label_position,
            y_offset - 1 * y_spacing,
            "E2:",
            fontsize=label_fontsize,
            weight="bold",
            transform=plt.gca().transAxes,
        )
        plt.text(
            e_x_value_position,
            y_offset - 1 * y_spacing,
            E[1],
            fontsize=value_fontsize,
            transform=plt.gca().transAxes,
        )
        plt.text(
            e_x_label_position,
            y_offset - 2 * y_spacing,
            "E3:",
            fontsize=label_fontsize,
            weight="bold",
            transform=plt.gca().transAxes,
        )
        plt.text(
            e_x_value_position,
            y_offset - 2 * y_spacing,
            E[2],
            fontsize=value_fontsize,
            transform=plt.gca().transAxes,
        )
        plt.text(
            e_x_label_position,
            y_offset - 3 * y_spacing,
            "E4:",
            fontsize=label_fontsize,
            weight="bold",
            transform=plt.gca().transAxes,
        )
        plt.text(
            e_x_value_position,
            y_offset - 3 * y_spacing,
            E[3],
            fontsize=value_fontsize,
            transform=plt.gca().transAxes,
        )

        plt.text(
            s_x_label_position,
            y_offset,
            "S1 (...-E1):",
            fontsize=label_fontsize,
            weight="bold",
            transform=plt.gca().transAxes,
        )
        plt.text(
            s_x_value_position,
            y_offset,
            S[0],
            fontsize=value_fontsize,
            transform=plt.gca().transAxes,
        )
        plt.text(
            s_x_label_position,
            y_offset - 1 * y_spacing,
            "S2 (...-E2):",
            fontsize=label_fontsize,
            weight="bold",
            transform=plt.gca().transAxes,
        )
        plt.text(
            s_x_value_position,
            y_offset - 1 * y_spacing,
            S[1],
            fontsize=value_fontsize,
            transform=plt.gca().transAxes,
        )
        plt.text(
            s_x_label_position,
            y_offset - 2 * y_spacing,
            "S3 (...-E3):",
            fontsize=label_fontsize,
            weight="bold",
            transform=plt.gca().transAxes,
        )
        plt.text(
            s_x_value_position,
            y_offset - 2 * y_spacing,
            S[2],
            fontsize=value_fontsize,
            transform=plt.gca().transAxes,
        )
        plt.text(
            s_x_label_position,
            y_offset - 3 * y_spacing,
            "S4 (...-E4):",
            fontsize=label_fontsize,
            weight="bold",
            transform=plt.gca().transAxes,
        )
        plt.text(
            s_x_value_position,
            y_offset - 3 * y_spacing,
            S[3],
            fontsize=value_fontsize,
            transform=plt.gca().transAxes,
        )

    svg_file_path = os.path.join(folder_path, file_number + "_quick_analysis.svg")
    plt.savefig(svg_file_path, bbox_inches="tight")
    plt.close()


def bell_matrix(matrix, folder_path, file_number):
    print("Coming Soon.")

    # generate coincidence matrix
    bell_angles_for_bob = [22.5, 67.5, 112.5, 157.5]
    bell_angles_for_bob_indices = [
        B_detector_angles.index(angle) for angle in bell_angles_for_bob
    ]
    coincidence_matrix = data[:, bell_angles_for_bob_indices]
    coincidence_matrix[1], coincidence_matrix[2] = (
        coincidence_matrix[2].copy(),
        coincidence_matrix[1].copy(),
    )
    coincidence_matrix[:, 1], coincidence_matrix[:, 2] = (
        coincidence_matrix[:, 2].copy(),
        coincidence_matrix[:, 1].copy(),
    )
    print(coincidence_matrix)

    # calculate Bell value
    E, S = calc_e_s(coincidence_matrix)

    # Define colormap
    colormap = plt.colormaps.get_cmap("coolwarm")

    # Normalize the values in the matrix to range [0, 1]
    normalized_matrix = (coincidence_matrix - np.min(coincidence_matrix)) / (
        np.max(coincidence_matrix) - np.min(coincidence_matrix)
    )

    # Generate colors based on colormap and normalized values
    cell_colors = [[colormap(value) for value in row] for row in normalized_matrix]

    # Display matrix in tabular format below the plot
    coincidence_table = plt.table(
        cellText=coincidence_matrix,
        cellColours=cell_colors,
        rowLabels=["V", "H", "D", "A"],
        colLabels=["22.5°", "112.5°", "67.5°", "157.5°"],
        loc="bottom",
        cellLoc="center",
        bbox=[0, -0.5, 0.4, 0.35],
    )

    label_fontsize = 15
    value_fontsize = 15
    y_offset = -0.22
    y_spacing = 0.08
    x_offset = 0.55
    e_x_label_position = x_offset
    e_x_value_position = 0.05 + x_offset
    s_x_label_position = 0.15 + x_offset
    s_x_value_position = 0.29 + x_offset

    plt.text(
        e_x_label_position,
        y_offset,
        "E1:",
        fontsize=label_fontsize,
        weight="bold",
        transform=plt.gca().transAxes,
    )
    plt.text(
        e_x_value_position,
        y_offset,
        E[0],
        fontsize=value_fontsize,
        transform=plt.gca().transAxes,
    )
    plt.text(
        e_x_label_position,
        y_offset - 1 * y_spacing,
        "E2:",
        fontsize=label_fontsize,
        weight="bold",
        transform=plt.gca().transAxes,
    )
    plt.text(
        e_x_value_position,
        y_offset - 1 * y_spacing,
        E[1],
        fontsize=value_fontsize,
        transform=plt.gca().transAxes,
    )
    plt.text(
        e_x_label_position,
        y_offset - 2 * y_spacing,
        "E3:",
        fontsize=label_fontsize,
        weight="bold",
        transform=plt.gca().transAxes,
    )
    plt.text(
        e_x_value_position,
        y_offset - 2 * y_spacing,
        E[2],
        fontsize=value_fontsize,
        transform=plt.gca().transAxes,
    )
    plt.text(
        e_x_label_position,
        y_offset - 3 * y_spacing,
        "E4:",
        fontsize=label_fontsize,
        weight="bold",
        transform=plt.gca().transAxes,
    )
    plt.text(
        e_x_value_position,
        y_offset - 3 * y_spacing,
        E[3],
        fontsize=value_fontsize,
        transform=plt.gca().transAxes,
    )

    plt.text(
        s_x_label_position,
        y_offset,
        "S1 (...-E1):",
        fontsize=label_fontsize,
        weight="bold",
        transform=plt.gca().transAxes,
    )
    plt.text(
        s_x_value_position,
        y_offset,
        S[0],
        fontsize=value_fontsize,
        transform=plt.gca().transAxes,
    )
    plt.text(
        s_x_label_position,
        y_offset - 1 * y_spacing,
        "S2 (...-E2):",
        fontsize=label_fontsize,
        weight="bold",
        transform=plt.gca().transAxes,
    )
    plt.text(
        s_x_value_position,
        y_offset - 1 * y_spacing,
        S[1],
        fontsize=value_fontsize,
        transform=plt.gca().transAxes,
    )
    plt.text(
        s_x_label_position,
        y_offset - 2 * y_spacing,
        "S3 (...-E3):",
        fontsize=label_fontsize,
        weight="bold",
        transform=plt.gca().transAxes,
    )
    plt.text(
        s_x_value_position,
        y_offset - 2 * y_spacing,
        S[2],
        fontsize=value_fontsize,
        transform=plt.gca().transAxes,
    )
    plt.text(
        s_x_label_position,
        y_offset - 3 * y_spacing,
        "S4 (...-E4):",
        fontsize=label_fontsize,
        weight="bold",
        transform=plt.gca().transAxes,
    )
    plt.text(
        s_x_value_position,
        y_offset - 3 * y_spacing,
        S[3],
        fontsize=value_fontsize,
        transform=plt.gca().transAxes,
    )

    svg_file_path = os.path.join(folder_path, file_number + "_quick_analysis.svg")
    plt.savefig(svg_file_path, bbox_inches="tight")
    plt.close()
