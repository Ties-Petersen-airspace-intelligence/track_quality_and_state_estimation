// What other modules call when something changed; main.js fills these in, so no module imports main.
export const bus = {
  draw: () => {},            // redraw the map, the timeline and the charts' data
  rebuildCharts: () => {},   // the compare list or the charts changed
  redrawCharts: () => {},    // time now or the hover changed
  renderCompare: () => {},
  renderStrategies: () => {},
};
