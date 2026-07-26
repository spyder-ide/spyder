# %% sig
def terrain_model(file, grid_size=10, buffer_val=20, figsize=(12,12),
                  plot=True, plot_grid=True, mp=True,
                  path2asc=r'O:\Diverse\EDW\Master\Terrænmodel 10m grid\\'):
# %% body
    model = GeoDataFrame(file).geom_fix().buffer(buffer_val=buffer_val)
    bounds = model.bounds_buf
    buffer = model.gdf_buf
    if plot is True:
        plot_gdf(model.gdf, title='GIS data', figsize=figsize)
    print('Filtering ASC files')
    asc_files = AscIndex(path=path2asc).filter_asc(bounds=bounds)
    if plot_grid is True:
        geoms = [AscFile(file, load=False).read_info().coordslist for file in asc_files]
        asc_poly2gdf(geoms, model.gdf)

    if mp is True:
        asc_slice_ray = ray.remote(asc_slice)
        futures = [asc_slice_ray.remote(file, buffer, grid_size, model.crs) for file in asc_files]
        results = ray.get(futures)
    elif mp is False:
        # for file in asc_files:
        results = [asc_slice(file, buffer, grid_size, model.crs) for file in asc_files]
    terrain_slices = pd.concat(results)
    if plot is True:
        plot_gdf_sample(model.gdf, terrain_slices, title='Sliced terrain data')
    return terrain_slices
# %% numpy
    """
    SUMMARY.

    Parameters
    ----------
    file : TYPE
        DESCRIPTION.
    grid_size : TYPE, optional
        DESCRIPTION. The default is 10.
    buffer_val : TYPE, optional
        DESCRIPTION. The default is 20.
    figsize : TYPE, optional
        DESCRIPTION. The default is (12,12).
    plot : TYPE, optional
        DESCRIPTION. The default is True.
    plot_grid : TYPE, optional
        DESCRIPTION. The default is True.
    mp : TYPE, optional
        DESCRIPTION. The default is True.
    path2asc : TYPE, optional
        DESCRIPTION. The default is r'O:\Diverse\EDW\Master\Terrænmodel 10m grid\\'.

    Returns
    -------
    TYPE
        DESCRIPTION.
    """
# %% google
    """SUMMARY.

    Args:
        file (TYPE): DESCRIPTION.
        grid_size (TYPE, optional): DESCRIPTION. Defaults to 10.
        buffer_val (TYPE, optional): DESCRIPTION. Defaults to 20.
        figsize (TYPE, optional): DESCRIPTION. Defaults to (12,12).
        plot (TYPE, optional): DESCRIPTION. Defaults to True.
        plot_grid (TYPE, optional): DESCRIPTION. Defaults to True.
        mp (TYPE, optional): DESCRIPTION. Defaults to True.
        path2asc (TYPE, optional): DESCRIPTION. Defaults to r'O:\Diverse\EDW\Master\Terrænmodel 10m grid\\'.

    Returns:
        TYPE: DESCRIPTION.
    """
# %% sphinx
    """SUMMARY.

    :param file: DESCRIPTION
    :type file: TYPE
    :param grid_size: DESCRIPTION, defaults to 10
    :type grid_size: TYPE
    :param buffer_val: DESCRIPTION, defaults to 20
    :type buffer_val: TYPE
    :param figsize: DESCRIPTION, defaults to (12,12)
    :type figsize: TYPE
    :param plot: DESCRIPTION, defaults to True
    :type plot: TYPE
    :param plot_grid: DESCRIPTION, defaults to True
    :type plot_grid: TYPE
    :param mp: DESCRIPTION, defaults to True
    :type mp: TYPE
    :param path2asc: DESCRIPTION, defaults to r'O:\Diverse\EDW\Master\Terrænmodel 10m grid\\'
    :type path2asc: TYPE

    :rtype: TYPE
    :returns: DESCRIPTION
    """
