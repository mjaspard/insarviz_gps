# -*- coding: utf-8 -*-

# imports ###################################################################

from PyQt5.QtCore import (
    pyqtSlot
    )

from pyqtgraph import HistogramLUTWidget

# palette ###################################################################


class Palette(HistogramLUTWidget):
    def __init__(self, map_view, minimap_view):
        super().__init__()

        self.map_view = map_view
        self.minimap_view = minimap_view
        self.model = map_view.model
        self.model.texture_changed.connect(self.update_histogram)
        self.map_view.vs_changed.connect(self.update_bounds)

        self.sigLevelsChanged.connect(self.update_levels)
        self.model.init_histo_vals.connect(self.do_init_histo_vals)

        self.gradient.sigGradientChanged.connect(self.update_palette)

        self.gradient.showTicks(False)

        # self.regions[0].setVisible(False)
        # self.plots[0].setVisible(False)
        # self.gradient.levels[0].setVisible(False)

        # for now, remove hsv or non-linear gradients
        # (spectrum, cyclic, greyclip)
        self.gradient.menu.removeAction(self.gradient.hsvAction)
        for i, g in enumerate(self.gradient.menu.actions()):
            if i in [4, 5, 6]:
                self.gradient.menu.removeAction(g)

        # self.item.layout.addItem(self.item.axis, 0, 0)
        # print()
        # self.item.setLayout(self.item.layout)

    def update_bounds(self):
        self.setHistogramRange(self.map_view.v_i,
                               self.map_view.v_a)

    def update_histogram(self):
        self.plot.setData(*self.model.histograms[self.model.i])

    @pyqtSlot()
    def update_levels(self):
        """
        called when levels are changed by user

        Returns
        -------
        None.

        """
        mn, mx = self.getLevels()
        self.map_view.update_black(mn)
        self.map_view.update_white(mx)

        self.minimap_view.update_black(mn)
        self.minimap_view.update_white(mx)

    @pyqtSlot()
    def update_palette(self):
        self.map_view.set_colormap(
            colormap=bytes(
                self.gradient.colorMap().getColors().ravel().tolist()))
        self.gradient.showTicks(False)

    def do_init_histo_vals(self, vals):
        """
        called when first band is loaded to initialize histogram levels at
        first band's percentiles'

        Parameters
        ----------
        vals : tuple
            (lowest percentile, highest percentile) values for the initial
            histogram to be set at.

        Returns
        -------
        None.

        """
        vi, va = vals
        self.item.setLevels(vi, va)
        self.update_levels()
        try:
            self.axis.setLabel(units=self.model.loader.metadata['Value_unit'])
        except KeyError:
            self.axis.setLabel(units='Undefined units')

