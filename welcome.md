

Hi there!

You just set up a new LatexOutliner project.

You can press `?` in outline view to view the help file.
Or you can trigger `LatexOutliner: Show help` in the command palette.

Now just populate your outline, fill the text snippets with text, use `LatexOutliner: Update outline.tex` and build your tex file.
If you use LaTeXTools or something similar: main.tex is set as TEXRoot, so `super+B` works in every text snippet.

Most people should modify main.tex. The only important thing is to include the line `\input{outline.tex}`.

Have fun!
Nils


P.S.:
If you haven't it is probably a good idea to set up a short cut to update outline.tex. You can add something like this to your user shortcuts (SublimeText -> Preferences -> Key Bindings - User):

```
[
    { "keys": ["super+shift+u"], "command": "latex_outliner_update_outline_tex" }
]
```

If you prefer not to, command palette LOU is also quick and does the trick for me.
