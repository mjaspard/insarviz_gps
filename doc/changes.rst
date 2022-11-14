=============
Release Notes
=============


1.0.3 (2022-09-16)
------------------

New 
```

- Profile tool now links two points selected by the user, and draws plots for a selection of points (regular spacing) on this profile line (`!55 <https://gricad-gitlab.univ-grenoble-alpes.fr/deformvis/insarviz/-/merge_requests/55>`_)
- Points tool now allows user to select individual points whose data are to be plotted (`!55 <https://gricad-gitlab.univ-grenoble-alpes.fr/deformvis/insarviz/-/merge_requests/55>`_)
- Reference tool: once data is plotted from Profile or Points tool, a reference point or zone (rectangle) can be selected on the Map by the user, plots will be adjusted to the reference (`!55 <https://gricad-gitlab.univ-grenoble-alpes.fr/deformvis/insarviz/-/merge_requests/55>`_)


Fixed
`````
- lock axes button on plots did not work on Linux (`#56 <https://gricad-gitlab.univ-grenoble-alpes.fr/deformvis/insarviz/-/issues/56>`_)
- export to csv was faulty when more than one curve on plot ('#66 <https://gricad-gitlab.univ-grenoble-alpes.fr/deformvis/insarviz/-/issues/66>)


Changed
```````
- Profile tool renamed Points (see New section)
- Documentation updated