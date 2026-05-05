# FlyPredictome Network

Interactive exploration of the *Drosophila* protein-protein interaction network from FlyPredictome — 1.5 million AlphaFold-Multimer predictions scored with iLIS.

**[Open Viewer](https://flyark.github.io/FlyPredictome-network)**

## Network

From 1.5 million pairwise predictions, 147,410 heterodimeric PPIs were classified as positive (iLIS ≥ 0.223). To construct this network, we selected positive PPIs supported by fly literature (FlyBase, BioGRID, MIST) or conserved interologs (DIOPT ≥ 4). After filtering for degree ≥ 2 and extracting the giant connected component:

**5,224 proteins | 21,657 PPIs | 31 clusters**

Leiden community detection identified 31 clusters, each corresponding to a coherent functional theme. Recursive sub-clustering resolved a three-level hierarchy from pathway-level modules down to individual protein complexes.

## Features

- **Cluster view** — global network colored by cluster, zoom and pan
- **Grid view** — sub-cluster tiles with sub-group coloring
- **Evidence filtering** — fly only, interolog only, both
- **FPR filtering** — ≤10%, ≤5%, ≤1%
- **Gene search** — find any protein and its interactions
- **GO enrichment** — top terms for BP, MF, and CC per cluster
- **Export** — download filtered edge lists as CSV

## Links

- [FlyPredictome Database](https://www.flyrnai.org/tools/fly_predictome) — predicted structures, PAE maps, iLIS scores
- [LIVIA](https://flyark.github.io/LIVIA) — interactive 3D structure visualization
- [AFM-LIS](https://github.com/flyark/AFM-LIS) — iLIS analysis pipeline

## Citation

If you use FlyPredictome in your research, please cite:

> Kim, A.-R., Comjean, A., Veal, A., Rodiger, J., Han, M., Hu, Y., & Perrimon, N. (2026). FlyPredictome: A structural atlas of predicted protein-protein interactions in *Drosophila*. *bioRxiv*. https://doi.org/10.64898/2026.04.14.718529

```bibtex
@article{kim2026flypredictome,
  title   = {FlyPredictome: A structural atlas of predicted protein-protein interactions in {Drosophila}},
  author  = {Kim, Ah-Ram and Comjean, Aram and Veal, Austin and Rodiger, Jonathan and Han, Myeonghoon and Hu, Yanhui and Perrimon, Norbert},
  journal = {bioRxiv},
  year    = {2026},
  month   = apr,
  doi     = {10.64898/2026.04.14.718529},
  url     = {https://doi.org/10.64898/2026.04.14.718529}
}
```
