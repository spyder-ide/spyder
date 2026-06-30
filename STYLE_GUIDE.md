# Style guide to Spyder localization

## Purpose of this document

This document defines the localization guidelines used in Spyder to improve readability, consistency and maintainability.

The wording and presentation of UI text affects usability and user understanding. Defining common guidelines helps maintain consistency across the application and improves the overall user experience.

These guidelines apply to both developers defining source strings and translators contributing through Crowdin.

## Localization workflow

Source strings are defined in the Spyder codebase in English and extracted into a POT template file. Translations are then provided through language-specific PO files based on this template.

Localization is managed through the [Crowdin](http://crowdin.com/) platform. The Spyder project is available at [https://crowdin.com/project/spyder](https://crowdin.com/project/spyder).

## General principles

The following principles apply to all interface text in Spyder.

**Keep it simple and clear:** use short and clear sentences, avoid unnecessary wording, focus on essential information.

**Use consistent terminology:** always use the same terms for the same concepts, prefer conventional terminology.

**Use placeholders:** reference existing UI elements (typically menu entries) through placeholders whenever possible instead of duplicating labels in text.

## Guidelines

To ensure consistency across similar contexts, Spyder strings can be grouped into three categories, each with its own guidelines.

### Titles

Titles identify a UI element or container (windows, pane, menu).

**Examples**
- Menu and submenu titles (e.g., `File`, `Edit`, `Toolbars`)
- Window titles (e.g., `Preferences`, `Warning`)
- Tab titles (e.g., `Debugger`, `Profiler`, `Console 1/A`, `Outline`)

**Guidelines**
- Keep titles short and descriptive
- Prefer one word only whenever possible
- Users should immediately understand the purpose of the element
- Typography: use sentence case, do not end with a period

### Actions

Actions strings describe something the user can do.

**Examples**
- Dialog buttons (e.g., "OK", "Cancel", "Reset")
- Menu items (e.g., "Open file", "Run cell")
- Tooltips and action labels (e.g., "Open file", "Run cell")

**Guidelines**
- Keep actions short and explicit
- Prefer familiar and widely used UI terminology whenever possible
- Actions should generally follow the pattern `<verb> + [<noun>]`
- *Typography:* use sentence case, do not end with a period
- *Typography:* use the ellipsis character (`…`) instead of three dots (`...`) for action that open a dialog or require additional input
- *Developers:* reuse existing Qt Actions whenever possible instead of duplicating strings

Established UI conventions should be followed even when they differ from the recommended pattern (for example, `New file` instead of `Create file`).

### Explanations

Explanation strings provide additional context or instructions when titles and actions are not sufficient.

**Examples**
- Preference descriptions (e.g., `Select the default Python interpreter for (...)`, `UMR forces Python to reload (...)`) 
- Help tooltips (e.g., `Display the time since the current console was started in the tab bar`)
- Status bar descriptions (e.g., `Search text in multiple file with the Find pane`)

**Guidelines**
- Avoid explanation strings unless they add useful information (try to improve titles and actions first)
- Keep explanations short and easy to read
- Reference existing UI elements through placeholders whenever possible instead of duplicating their labels in text
- Use HTML tags sparingly and only when they provide a clear benefit (see specific cases below)
- *Typography:* use sentence case, end with a period

**HTML usage**
- `<br>` : line breaks
  - Use only to separate paragraphs
  - Do not use to manually control text width (this is done automatically)
- `<code>` : inline code
  - Use for commands, variables, or filenames
- `<b>`, `<i>`, `<tt>` : other formatting
  - Avoid unless strictly necessary

## Language specific guidelines

### French

(...)


### Other languages

Contributors are encouraged to propose language-specific guidelines (terminology, typography, ...). These guidelines should follow the general principles and guidelines defined in this document whenever possible.