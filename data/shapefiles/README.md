# Shapefiles

The choropleth maps in `UMC_Final.ipynb` require the **Natural Earth 110m Admin 0 Countries** shapefile.

## One-time setup (required for offline/replication use)

Download the zip and place it in this directory:

```
URL:  https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip
Save as:  data/shapefiles/ne_110m_admin_0_countries.zip
```

Or run this from the project root:

```bash
curl -L -o data/shapefiles/ne_110m_admin_0_countries.zip \
  "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"
```

If the file is absent, the notebook will attempt a live download automatically (requires internet access at run time). The file is ~400 KB and is excluded from version control via `.gitignore` because it is a third-party dataset.
