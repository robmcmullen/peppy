***********
Search Mode
***********

.. _search:

Search Mode scans through a set of files looking for matches.  It is similar
to the 'grep' command in unix, but is much more powerful because it can be
extended to search for matches based on context or based on characteristics in
certain types of files.


The Search Window
=================

.. image:: peppy-search-mode.jpg
   :align: center

The main search mode window is split into two parts, the top is for entering
search criteria, and the bottom is a list that displays the results of the
search.

Search Criteria
---------------

There are four sections to the search criteria: the search string, the type of
search, how to choose the files to search, and the files to ignore.

.. image:: peppy-search-criteria.png
   :align: center

The first line is the search string, which in the simplest case is the exact
string that you wish to find.  In more complex cases, it can be a regular
expression, a comparison, or another format depending on the type of search.

The type of search is what makes Peppy's search so powerful.  The type is
selected by a pull-down list, and additional types can be added through
plugins.  The default search types are **Text Search** which provides the usual
text search operations (whether or not the case is significant, and regular
expressions for advanced pattern matching), and **Numeric Search** which scans
through text files and compares numbers that it finds with the comparison
defined by the search string.  The search types are described in more detail
in the following section.

Files can be chosen in a number of ways by selecting from a pull-down list.
(Note this can also be extended by plugins.) Currently, the available options
are **Directory**, **Project**, and **Open Documents**.  The **Directory** option
will perform its search starting with all files in the named directory, and
continue recursively through all subdirectories.  The **Project** option will
limit itself to only those files contained in the selected project (see
:ref:`projects` for more information and how to define projects).  The **Open
Documents** option limits the search to only those documents that are already
open in peppy; that is, only those documents that appear in the ''Documents''
menu.

Finally, the **Ignore Names** criteria is a list of filename extensions to skip
in the search process.

Pressing the **Start** button (or using either the **Actions -> Start Search**
menu item or the start search icon on the toolbal) will begin the search
process.  An error that causes the search to fail will show up in the status
bar, otherwise the search will display results as they are discovered.  Note
that you can continue to work in other tabs or peppy windows as the search
operates because the search is performed in a separate thread.




