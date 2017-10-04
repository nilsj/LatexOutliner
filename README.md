# LatexOutliner for SublimeText

Work in progress!

[Scrivener][scr]-style latex editing for SublimeText.

The technical realization is inspired by the [FileBrowser][fb] plugin.

[scr]: https://www.literatureandlatte.com/scrivener.php
[fb]: https://github.com/aziz/SublimeFileBrowser

## What does it?

LatexOutliner shows a sidebar with an outline of your project.
You can add text snippets and rearrange them.
Under the hood, LatexOutliner keeps an outline.tex which you can include wherever you want, e.g. in a master.tex file.
You can also group them under headers.
Of course, you can nest headers, and move items around, all using vim style keybindings.

See [the help file](help.md) for currently implemented functionality.

## Set up
- Clone this repository to your packages directory
- Save a new project in SublimeText
- Command palette: "LatexOutliner: Set up project"
- press `?` in the outline view for help
- If the outline view is not visible later on, use "LatexOuteliner: Show outline on the left" in the command palette.

### Beamer
If you set the "beamer" property to true in the project settings, then each text snippet will be surrounded by a frame, and the frame title will be the title of the text snippet.

## Todos
- move cursor with j,k (for non-vintageous users)
- Enable build tex from outline view

### Later
- export outline to filesystem
- import outline from filesystem
- move cursor to open text snippet in focus
- nicer style for outline view (check dired.hiddentmTheme)
- hide cursor?

### Wishlist
- Drag'n'Drop outline
- Context menus for mouse interaction
