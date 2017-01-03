#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sublime import message_dialog, packages_path, Region, ok_cancel_dialog
from sublime_plugin import WindowCommand, TextCommand
from os.path import join, dirname, isdir
from os import mkdir, listdir
from shutil import copyfile
from itertools import count
from json import dump, load
from functools import partial


OUTLINE_JSON = "outline.json"
OUTLINE_TEX_DISCLAIMER = (
    "% This file is populated automatically with " +
    "\"LatexOutliner: Update outline.tex\".")
OUTLINE_DIRECTORY = "outline"
NEW_SNIPPETS_DIRECTORY = "new text snippets"


# the actual outlines (tree)
_outline = {}
# a pointer to the current subtree
_current_subtree = {}
# maps line number back to tree items
_index = {}


def plugin_unloaded():
    for project_path in _outline:
        dump_outline(project_path)
    # idea: close all outline views


def get_outline(project_path):
    if project_path not in _outline:
        _outline[project_path] = load_outline(project_path)
    return _outline[project_path]


def dump_outline(project_path):
    with open(join(project_path, OUTLINE_JSON), 'w', encoding='utf-8') as f:
        dump(_outline[project_path].getJson(), f, indent=2)


def load_outline(project_path):
    with open(join(project_path, OUTLINE_JSON), 'r', encoding='utf-8') as f:
        outline = Heading.fromJson(load(f))
    return outline


def get_current_substree(project_path):
    if project_path not in _current_subtree:
        _current_subtree[project_path] = get_outline(project_path)
    return _current_subtree[project_path]


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
        # idea: ask if beamer should be set to true
        # todo: check how to write true in settings
        project_data['beamer'] = False
        # set TEXroot
        if 'settings' not in project_data:
            project_data['settings'] = {}
        project_data['settings']['TEXroot'] = "main.tex"
        project_data['settings']['line_numbers'] = false

        # write project settings
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
        # create emtpy outline.tex
        outline_file = join(project_root, "outline.tex")
        with open(outline_file, 'w', encoding='utf-8') as f:
            f.write(OUTLINE_TEX_DISCLAIMER)

        # idea: warn if directories already exist
        # create outline and new text snippets folders
        outline_directory = join(project_root, OUTLINE_DIRECTORY)
        if not isdir(outline_directory):
            mkdir(outline_directory)
        # idea: generate outline from filesystem if outline directory
        new_snippets_directory = join(project_root, NEW_SNIPPETS_DIRECTORY)
        if not isdir(new_snippets_directory):
            mkdir(new_snippets_directory)
            # idea: warn that new_snippets is not emtpy

        outline = Heading("Outline")
        outline.expanded = True
        _outline[project_root] = outline
        # ask if an example outline should be created
        example_outline = ok_cancel_dialog(
             "Should an example outline be created?", "Create example outline")
        if example_outline:
            for i in range(3):
                section = Heading("Section "+str(i+1))
                outline.appendChild(section)
                for j in range(4):
                    text = TextSnippet("Text Snippet "+str(j+1), "",
                                       project_root)
                    section.appendChild(text)

        self.window.run_command("latex_outliner")

        welcome_file = join(LO_path, "welcome.md")
        welcome_view = self.window.open_file(welcome_file)
        welcome_view.set_read_only(True)
        welcome_view.set_scratch(True)
        self.window.set_view_index(welcome_view, 1, 0)

        return


class LatexOutlinerCommand(WindowCommand):
    """
    Show the outline in a new view in new group to the left
    """
    def run(self):
        # todo: Determine the number of groups and set up a new layout
        # with one more group
        # set up a two group layout
        width = 0.3
        self.window.set_layout({"cols": [0.0, width, 1.0],
                                "rows": [0.0, 1.0],
                                "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})

        # move all other views one group to the right
        for group in reversed(range(self.window.num_groups())):
            for view in reversed(self.window.views_in_group(group)):
                self.window.set_view_index(view, group+1, 0)

        # create the new view and move it to the leftmost group
        view = self.window.new_file()
        # idea: hide line numbers
        self.window.set_view_index(view, 0, 0)
        view.set_scratch(True)
        view.set_syntax_file(
            'Packages/LatexOutliner/LatexOutliner.hidden-tmLanguage')
        view.run_command("populate_outline_view")


class PopulateOutlineViewCommand(TextCommand):
    """
    Populates the outline view
    """
    def run(self, edit, cursorline=0):
        view = self.view
        view.set_read_only(False)
        # clear view
        view.erase(edit, Region(0, view.size()))
        # walk outline and insert in view
        project_root = dirname(view.window().project_file_name())
        current_subtree = get_current_substree(project_root)
        view.set_name(current_subtree.caption)
        global _index
        _index[project_root] = self.showOutlineStart(edit, current_subtree)
        # set the cursor position
        point = view.text_point(cursorline, 0)
        view.show(point)
        view.sel().clear()
        view.sel().add(Region(point))
        view.set_read_only(True)
        # todo: find better place, only when the outline got changed
        # dump outline to be save
        dump_outline(project_root)
        # update outline.tex
        view.window().run_command("latex_outliner_update_outline_tex")

    def showOutlineStart(self, edit, currentSubtree):
        lineCount = count()
        index = []
        for child in currentSubtree.children:
            index.extend(self.showOutline(edit, child, lineCount))
        return index

    def showOutline(self, edit, item, lineCount, level=0, indent='  '):
        if type(item) is Heading:
            if item.expanded:
                text = indent*level+"▾ "+item.caption+"\n"
            else:
                text = indent*level+"▸ "+item.caption+"\n"
        elif type(item) is TextSnippet:
            text = indent*level+"≡ "+item.caption+"\n"
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


# todo: alle aufrufe von TextSnippet checken und eine leere annotation reinschreiben
class TextSnippet():
    def __init__(self, caption, annotation, path, fresh=True):
        """
        if fresh, path is the project_root,
        otherwise it is the path
        """
        self.caption = caption
        self.annotation = annotation
        if fresh:
            self.path = self.get_fresh_file(path)
        else:
            self.path = path

    def get_fresh_file(self, project_root):
        abs_path_to_new_snippets = join(project_root, NEW_SNIPPETS_DIRECTORY)
        existing_files = listdir(abs_path_to_new_snippets)
        i = len(existing_files)
        while True:
            fresh_name = "textSnippet"+str(i)+".tex"
            if fresh_name not in existing_files:
                break
            i += 1
        full_fresh_name = join(abs_path_to_new_snippets, fresh_name)
        with open(full_fresh_name, 'w', encoding='utf-8'):
            pass
        return join(NEW_SNIPPETS_DIRECTORY, fresh_name)

    def getJson(self):
        if not hasattr(self, "annotation"):
            self.annotation = ""
        return {'class': 'TextSnippet',
                'caption': self.caption,
                'path': self.path,
                'annotation': self.annotation,
                }

    @staticmethod
    def fromJson(json):
        # todo: annotation check soll irgendwann raus, ist jetzt erstmal
        # aus Kompatibilitätsgründen drin
        if 'annotation' not in json:
            json['annotation'] = ""
        text = TextSnippet(json['caption'], json['annotation'],
                           json['path'], fresh=False)
        return text


def getItemUnderCursor(view):
    line = view.rowcol(view.sel()[0].a)[0]
    path = dirname(view.window().project_file_name())
    # if _index[path] is not set, outline view is dead and should be refreshed
    if path not in _index:
        view.run_command("populate_outline_view", {'cursorline': line})
        return None
    if line < len(_index[path]):
        item = _index[path][line]
        return item
    else:
        return None


def openTextSnippet(item, window):
    project_root = dirname(window.project_file_name())
    text_snippet_path = join(project_root, item.path)
    new = window.open_file(text_snippet_path)
    # todo: if view already open, only focus, do not bring to first position
    window.set_view_index(new, 1, 0)


class LatexOutlinerOpenTextSnippetOrZoomIn(TextCommand):
    def run(self, edit):
        view = self.view
        item = getItemUnderCursor(view)
        if type(item) is TextSnippet:
            openTextSnippet(item, view.window())
        elif type(item) is Heading:
            project_root = dirname(view.window().project_file_name())
            _current_subtree[project_root] = item
            item.expanded = True
            view.run_command("populate_outline_view", {'cursorline': 0})


class LatexOutlinerClickCommand(TextCommand):
    def run(self, edit):
        view = self.view
        syntax = view.settings().get('syntax')
        if syntax == 'Packages/LatexOutliner/LatexOutliner.hidden-tmLanguage':
            item = getItemUnderCursor(view)
            if type(item) is TextSnippet:
                openTextSnippet(item, view.window())
            elif type(item) is Heading:
                item.expanded = not item.expanded
                line = item.linenumber
                view.run_command("populate_outline_view", {'cursorline': line})


class LatexOutlinerZoomOutCommand(TextCommand):
    def run(self, edit):
        view = self.view
        project_root = dirname(view.window().project_file_name())
        current_subtree = get_current_substree(project_root)
        if current_subtree.parent:
            global _current_subtree
            new_subtree = current_subtree.parent
            _current_subtree[project_root] = new_subtree
            item = getItemUnderCursor(view)
            # the new line is the sum of all recursive visible children
            # of the new_subtree before the selected item
            # this includes the current loop item for each execution
            # except the first
            line = -1
            if not item:
                item = current_subtree
            while item != new_subtree:
                line += 1
                # test for simple case
                position = item.parent.children.index(item)
                for i in range(position):
                    previous_child = item.parent.children[i]
                    line += 1
                    if type(previous_child) is Heading:
                        line += previous_child.getNumberOfChildren(
                            onlyVisible=True)
                item = item.parent
            view.run_command("populate_outline_view", {'cursorline': line})


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
        elif (type(item) is TextSnippet or
              type(item) is Heading and not item.expanded):
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
                          newItemClass="Heading" if heading else "TextSnippet",
                          selectedItem=item)
        user_info = "Create new "+("Heading" if heading else "TextSnippet")
        view.window().show_input_panel(caption=user_info,
                                       initial_text="",
                                       on_done=on_done,
                                       on_change=None,
                                       on_cancel=None)

    def createNewItem(self, caption, newItemClass, selectedItem):
        project_root = dirname(self.view.window().project_file_name())
        if newItemClass == "Heading":
            new_item = Heading(caption)
        elif newItemClass == "TextSnippet":
            new_item = TextSnippet(caption, "", project_root)

        if selectedItem is None:
            current_subtree = get_current_substree(project_root)
            current_subtree.appendChild(new_item)
            line = current_subtree.getNumberOfChildren(onlyVisible=True)-1
        elif type(selectedItem) is Heading and selectedItem.expanded:
            selectedItem.insertChildAt(new_item, 0)
            line = selectedItem.linenumber + 1
        else:
            new_parent = selectedItem.parent
            new_position = new_parent.children.index(selectedItem) + 1
            new_parent.insertChildAt(new_item, new_position)
            line = selectedItem.linenumber + 1
        self.view.run_command("populate_outline_view", {'cursorline': line})


class LatexOutlinerRenameItemCommand(TextCommand):
    def run(self, edit):
        view = self.view
        item = getItemUnderCursor(view)
        on_done = partial(self.renameItem,
                          selectedItem=item)
        view.window().show_input_panel(caption="Rename",
                                       initial_text=item.caption,
                                       on_done=on_done,
                                       on_change=None,
                                       on_cancel=None)

    def renameItem(self, caption, selectedItem):
        selectedItem.caption = caption
        line = selectedItem.linenumber
        self.view.run_command("populate_outline_view", {'cursorline': line})


class LatexOutlinerEditAnnotationCommand(TextCommand):
    def run(self, edit):
        view = self.view
        item = getItemUnderCursor(view)
        if type(item) is not TextSnippet:
            return
        # todo: der check ob das snippet ein Attribut annotation hat
        # ist nur für den Übergang, und soll später raus
        if not hasattr(item, "annotation"):
            item.annotation = ""
        on_done = partial(self.changeAnnotation,
                          selectedItem=item)
        view.window().show_input_panel(caption="Edit Frame Annotation",
                                       initial_text=item.annotation,
                                       on_done=on_done,
                                       on_change=None,
                                       on_cancel=None)

    def changeAnnotation(self, annotation, selectedItem):
        selectedItem.annotation = annotation
        # note: it would be sufficient to just regenerate outline.json and .tex
        line = selectedItem.linenumber
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


class LatexOutlinerUpdateOutlineTex(WindowCommand):
    def run(self):
        project_root = dirname(self.window.project_file_name())
        outline = get_outline(project_root)

        lines = [OUTLINE_TEX_DISCLAIMER, '']
        project_data = self.window.project_data()
        beamer = project_data['beamer']
        lines.extend(self.traverseOutline(outline, beamer=beamer))
        outline_file = join(project_root, "outline.tex")
        with open(outline_file, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line+"\n")

    def traverseOutline(self, item, level=-1, beamer=False):
        indent = '  '
        lines = []
        if type(item) is Heading:
            # if item is not root element add section title
            if item.parent:
                lines.append('')
                lines.append(indent*level+self.levelHeading(
                    level, item.caption))
            for child in item.children:
                lines.extend(self.traverseOutline(child, level+1, beamer))
            lines.append('')
        elif type(item) is TextSnippet:
            if beamer:
                lines.append(indent*level+'\\begin{frame}')
                if item.annotation:
                    lines.append(indent*level+item.annotation)
                lines.append(indent*level+'\\frametitle{'+item.caption+'}')
            lines.append(indent*level+'\input{"'+item.path+'"}')
            if beamer:
                lines.append(indent*level+'\end{frame}')
            lines.append('')
        return lines

    # todo: read base_level from settings
    def levelHeading(self, level, title):
        headings = ['\section',
                    '\subsection',
                    '\subsubsection',
                    '\paragraph',
                    '\subparagraph',
                    ]
        return headings[level]+'{'+title+'}'


class LatexOutlinerShowHelpCommand(WindowCommand):
    def run(self):
        LO_path = join(packages_path(), "LatexOutliner")
        help_file = join(LO_path, "help.md")
        shortcut_view = self.window.open_file(help_file)
        self.window.set_view_index(shortcut_view, 1, 0)
        shortcut_view.set_read_only(True)
        shortcut_view.set_scratch(True)
