#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sublime import message_dialog, packages_path
from sublime_plugin import WindowCommand, TextCommand
from os.path import join, dirname
from shutil import copyfile
from itertools import count


# todo: load outline from disk in plugin_loaded
# todo: write outline to disk in plugin_unloaded
# todo: make outline dict so it supports multiple projects
outline = None


class SetUpLatexOutlinerProjectCommand(WindowCommand):
    """
    Ensure that a project is associated with the current window.
    Set up the new and outline folders. Set the isLatexOutlinerProject flag.
    """
    def run(self):
        project_data = self.window.project_data()
        # if there is no associated project, ask user to create one
        if project_data is None:
            message_dialog("Please create a project file!\n" +
                           "(Save Project As...)")
            # idea: hier ok_cancel benutzen und ok ruft Save Project As auf
            # leider weiß ich noch nicht, wie ich warten kann,
            # bis das Project erstellt wurde
            # idea: use delay oder time out oder so, und checke project_data
            # save_project_as
            return

        # idea: if folders are not set, ok_cancel to set to "."
        # set the project folder to '.'
        project_data['folders'] = [{'path': '.'}]
        # set TEXroot
        if 'settings' not in project_data:
            project_data['settings'] = {}
        project_data['settings']['TEXroot'] = "main.tex"

        # set outline and new folders
        project_data['outline_folder'] = "outline"
        project_data['new_folder'] = "new"

        # write project file
        self.window.set_project_data(project_data)

        # copy the example main file "main.tex" and open it
        project_root = dirname(self.window.project_file_name())
        LO_path = join(packages_path(), "LatexOutliner")
        orginal_main = join(LO_path, "main.tex")
        tex_root = join(project_root, "main.tex")
        copyfile(orginal_main, tex_root)
        # open main.tex
        self.window.open_file(tex_root)

        # idea: ask if an example outline should be created

        # note: wahrscheinlich muss die Struktur woanders gespeichert werden
        global outline
        outline = Heading("outline")
        for i in range(3):
            section = Heading("Section "+str(i+1))
            outline.appendChild(section)
            for j in range(4):
                text = TextSnippet("Text Snippet "+str(j+1))
                section.appendChild(text)

        return


class LatexOutlinerCommand(WindowCommand):
    """
    Show the outline in a new view in new group to the left
    """
    def run(self):
        # todo: Determine the number of groups and set up a new layout
        # with one more group
        # set up a two group layout
        self.window.set_layout({"cols": [0.0, 0.5, 1.0],
                                "rows": [0.0, 1.0],
                                "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})

        # # move all other views one group to the right
        # for group in reversed(range(self.window.num_groups())):
        #     for view in reversed(self.window.views_in_group(group)):
        #         self.window.set_view_index(view, group+1, 0)

        # create the new view and move it to the leftmost group
        view = self.window.new_file()
        self.window.set_view_index(view, 0, 0)
        view.set_scratch(True)
        view.set_name("Outline")
        view.run_command("populate_outline_view")


class PopulateOutlineViewCommand(TextCommand):
    """
    Populates the outline view
    """
    def run(self, edit):
        self.view.set_read_only(False)

        # todo: folding
        # walk outline and insert in view
        self.showOutline(edit, outline)

        self.view.set_read_only(True)

    def showOutline(self, edit, item, lineCount=count(), level=0, indent='  '):
        text = indent*level+item.caption+"\n"
        self.view.insert(edit,
                         self.view.text_point(next(lineCount), 0), text)
        if type(item) is Heading:
            for child in item.children:
                self.showOutline(edit, child, lineCount, level+1)


class Heading():
    def __init__(self, caption):
        self.caption = caption
        self.children = []

    def appendChild(self, child):
        self.children.append(child)


class TextSnippet():
    def __init__(self, caption):
        self.caption = caption
        # todo: create new file for snippet (?)
        self.path = get_fresh_path()


def get_fresh_path():
    i = 0
    # todo: set new_path_directory
    new_files_directory = "new"
    yield join(new_files_directory, "textSnippet"+str(i))
