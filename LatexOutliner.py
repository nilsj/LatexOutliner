#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sublime import message_dialog, packages_path, Region, ok_cancel_dialog
from sublime_plugin import WindowCommand, TextCommand
from os.path import join, dirname
from shutil import copyfile
from itertools import count
from json import dump, load
from functools import partial


# the actual outlines (tree)
_outline = {}
# maps line number back to tree items
_index = {}


def plugin_unloaded():
    for project_path in _outline:
        dump_outline(project_path)


def get_outline(project_path):
    if project_path not in _outline:
        _outline[project_path] = load_outline(project_path)
    return _outline[project_path]


OUTLINE_JSON = "outline.json"


def dump_outline(project_path):
    with open(join(project_path, OUTLINE_JSON), 'w', encoding='utf-8') as f:
        dump(_outline[project_path].getJson(), f, indent=2)


def load_outline(project_path):
    with open(join(project_path, OUTLINE_JSON), 'r', encoding='utf-8') as f:
        outline = Heading.fromJson(load(f))
    return outline


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
        # idea: use folders from settings
        project_root = dirname(self.window.project_file_name())
        LO_path = join(packages_path(), "LatexOutliner")
        orginal_main = join(LO_path, "main.tex")
        tex_root = join(project_root, "main.tex")
        copyfile(orginal_main, tex_root)
        # open main.tex
        self.window.open_file(tex_root)

        # idea: ask if an example outline should be created

        outline = Heading("Outline")
        outline.expanded = True
        for i in range(3):
            section = Heading("Section "+str(i+1))
            outline.appendChild(section)
            for j in range(4):
                text = TextSnippet("Text Snippet "+str(j+1))
                section.appendChild(text)
        _outline[project_root] = outline

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
        # idea: hide line numbers
        self.window.set_view_index(view, 0, 0)
        view.set_scratch(True)
        view.set_syntax_file(
            'Packages/LatexOutliner/LatexOutliner.hidden-tmLanguage')
        view.set_name("Outline")
        view.run_command("populate_outline_view")


class PopulateOutlineViewCommand(TextCommand):
    """
    Populates the outline view
    """
    def run(self, edit, cursorline=None):
        view = self.view
        view.set_read_only(False)
        # clear view
        view.erase(edit, Region(0, view.size()))
        # walk outline and insert in view
        project_root = dirname(view.window().project_file_name())
        global _index
        _index[project_root] = self.showOutline(edit,
                                                get_outline(project_root),
                                                count())
        # set the cursor position
        if cursorline:
            point = view.text_point(cursorline, 0)
            view.show(point)
            view.sel().clear()
            view.sel().add(Region(point))
        view.set_read_only(True)

    # idea: set caption of root element as view title
    def showOutline(self, edit, item, lineCount, level=0, indent='  '):
        if type(item) is Heading:
            if item.expanded:
                text = indent*level+"▾"+item.caption+"\n"
            else:
                text = indent*level+"▸"+item.caption+"\n"
        elif type(item) is TextSnippet:
            text = indent*level+"≡"+item.caption+"\n"
        line = next(lineCount)
        self.view.insert(edit, self.view.text_point(line, 0), text)
        item.linenumber = line
        index = [item]
        if type(item) is Heading and item.expanded:
            for child in item.children:
                index.extend(self.showOutline(edit, child, lineCount, level+1))
        return index


# todo: expanded in getJson and fromJson
class Heading():
    def __init__(self, caption):
        self.caption = caption
        self.parent = None
        self.children = []
        self.expanded = False

    def appendChild(self, child):
        self.children.append(child)
        child.parent = self

    def insertChildAt(self, item, position):
        self.children.insert(position, item)
        item.parent = self

    def removeChild(self, item):
        self.children.remove(item)

    def getNumberOfChildren(self, onlyVisible=False):
        number_of_children = 0
        if onlyVisible and not self.expanded:
            return number_of_children
        for child in self.children:
            number_of_children += 1
            if type(child) is Heading:
                number_of_children += child.getNumberOfChildren(
                    onlyVisible)
        return number_of_children

    def getJson(self):
        json = {'class': 'Heading',
                'caption': self.caption,
                'children': [],
                'expanded': self.expanded
                }
        for child in self.children:
            json['children'].append(child.getJson())
        return json

    @staticmethod
    def fromJson(json):
        heading = Heading(json['caption'])
        heading.expanded = json['expanded']
        for child in json['children']:
            if child['class'] == 'Heading':
                childClass = Heading
            elif child['class'] == 'TextSnippet':
                childClass = TextSnippet
            else:
                raise NameError("Unknown Class:", child['class'])
            heading.appendChild(childClass.fromJson(child))
        return heading


class TextSnippet():
    def __init__(self, caption, path=None):
        self.caption = caption
        if path:
            self.path = path
        else:
            # todo: create new file for snippet (?)
            self.path = caption + "_path"

    def getJson(self):
        return {'class': 'TextSnippet',
                'caption': self.caption,
                'path': self.path
                }

    @staticmethod
    def fromJson(json):
        text = TextSnippet(json['caption'], json['path'])
        return text


# todo: find good way to generate fresh file names
def get_fresh_path():
    i = 0
    # todo: set new_path_directory
    new_files_directory = "new"
    yield join(new_files_directory, "textSnippet"+str(i))


def getItemUnderCursor(view):
    line = view.rowcol(view.sel()[0].a)[0]
    path = dirname(view.window().project_file_name())
    if line < len(_index[path]):
        item = _index[path][line]
        return item
    else:
        return None


class LatexOutlinerOpenTextSnippet(TextCommand):
    def run(self, edit):
        view = self.view
        item = getItemUnderCursor(view)
        if type(item) is TextSnippet:
            new = view.window().open_file(item.path)
            # todo: if view already open, only focus
            view.window().set_view_index(new, 1, 0)
        elif type(item) is Heading:
            print("idea: implement zoom in")


class LatexOutlinerExpandCommand(TextCommand):
    def run(self, edit):
        view = self.view
        item = getItemUnderCursor(view)
        if type(item) is Heading and not item.expanded:
            item.expanded = True
            line = item.linenumber
            view.run_command("populate_outline_view", {'cursorline': line})


class LatexOutlinerCollapseCommand(TextCommand):
    def run(self, edit):
        view = self.view
        item = getItemUnderCursor(view)
        if type(item) is Heading and item.expanded:
            item.expanded = False
            line = item.linenumber
            view.run_command("populate_outline_view", {'cursorline': line})
        elif type(item) is TextSnippet:
            parent = item.parent
            if parent.parent:
                parent.expanded = False
                line = parent.linenumber
                view.run_command("populate_outline_view", {'cursorline': line})


class LatexOutlinerMoveUpCommand(TextCommand):
    def run(self, edit):
        view = self.view
        item = getItemUnderCursor(view)
        position = item.parent.children.index(item)
        if position == 0:
            return
        else:
            item.parent.removeChild(item)
            item.parent.insertChildAt(item, position-1)
            # new position is linenumber of switched sibling
            line = item.parent.children[position].linenumber
            view.run_command("populate_outline_view", {'cursorline': line})


class LatexOutlinerMoveDownCommand(TextCommand):
    def run(self, edit):
        view = self.view
        item = getItemUnderCursor(view)
        position = item.parent.children.index(item)
        if position == len(item.parent.children)-1:
            return
        else:
            item.parent.removeChild(item)
            item.parent.insertChildAt(item, position+1)
            # new position is linenumber of switched sibling
            # plus it's recursivley visible children
            # minus the recursivley visible children of the moved item
            switched_sibling = item.parent.children[position]
            line = switched_sibling.linenumber
            if type(switched_sibling) is Heading:
                line += switched_sibling.getNumberOfChildren(onlyVisible=True)
            if type(item) is Heading:
                line -= item.getNumberOfChildren(onlyVisible=True)
            view.run_command("populate_outline_view", {'cursorline': line})


class LatexOutlinerOutdentCommand(TextCommand):
    def run(self, edit):
        view = self.view
        item = getItemUnderCursor(view)
        # cannot move outside of tree
        if not item.parent.parent:
            return
        old_parent = item.parent
        old_parent.removeChild(item)
        parent_position = old_parent.parent.children.index(old_parent)
        old_parent.parent.insertChildAt(item, parent_position+1)
        # new line is the old parent's linenumber plus one plus, recursively,
        # all children and, if expanded, their children
        line = old_parent.linenumber + 1
        line += old_parent.getNumberOfChildren(onlyVisible=True)
        view.run_command("populate_outline_view", {'cursorline': line})


class LatexOutlinerIndentCommand(TextCommand):
    def run(self, edit):
        view = self.view
        item = getItemUnderCursor(view)
        # can only move inside if heading is above
        position = item.parent.children.index(item)
        if position == 0:
            return
        new_parent = item.parent.children[position-1]
        if type(new_parent) is not Heading:
            return
        item.parent.removeChild(item)
        new_parent.appendChild(item)
        new_parent.expanded = True
        # new line is parent's linenumber + all recursively visible children
        # minus the number of it's own visible children
        line = new_parent.linenumber + new_parent.getNumberOfChildren(
            onlyVisible=True)
        if type(item) is Heading:
            line -= item.getNumberOfChildren(onlyVisible=True)
        view.run_command("populate_outline_view", {'cursorline': line})


class LatexOutlinerCreateNewItemCommand(TextCommand):
    def run(self, edit, heading=True):
        view = self.view
        item = getItemUnderCursor(view)
        on_done = partial(self.createNewItem,
                          newItemClass=Heading if heading else TextSnippet,
                          selectedItem=item)
        user_info = "Create new "+("Heading" if heading else "TextSnippet")
        view.window().show_input_panel(caption=user_info,
                                       initial_text="",
                                       on_done=on_done,
                                       on_change=None,
                                       on_cancel=None)

    def createNewItem(self, caption, newItemClass, selectedItem):
        new_item = newItemClass(caption)
        if type(selectedItem) is Heading and selectedItem.expanded:
            selectedItem.insertChildAt(new_item, 0)
        else:
            new_parent = selectedItem.parent
            new_position = new_parent.children.index(selectedItem) + 1
            new_parent.insertChildAt(new_item, new_position)
        line = selectedItem.linenumber + 1
        self.view.run_command("populate_outline_view", {'cursorline': line})


class LatexOutlinerDeleteItemCommand(TextCommand):
    def run(self, edit):
        view = self.view
        item = getItemUnderCursor(view)
        if type(item) is Heading:
            child_count = item.getNumberOfChildren()
            message = "Delete {} and it's {} children?".format(
                item.caption, child_count)
        else:
            message = "Delete "+item.caption+"?"
        message += "\n(There is no undo.)"
        delete_ok = ok_cancel_dialog(message, "Delete "+item.caption)
        if not delete_ok:
            return
        else:
            line = item.linenumber
            item.parent.removeChild(item)
            self.view.run_command("populate_outline_view",
                                  {'cursorline': line})
