import os
import re
import time
from ast import literal_eval
from textwrap import wrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pathos.multiprocessing as mp
import plotly
import plotly.graph_objs as plotly_graph
from plotly.offline import plot

import magine.html_templates.html_tools as ht
from magine.data.formatter import pivot_table_for_export, log2_normalize_df

plotly.plotly.sign_in(username='james.ch.pino',
                      api_key='BnUcJSpmPcMKZg0yEFaL')

gene = 'gene'
protein = 'protein'
metabolites = 'metabolites'
meta_index = 'compound'
species_type = 'species_type'
sample_id = 'sample_id'
fold_change = 'treated_control_fold_change'
flag = 'significant_flag'
cm = plt.get_cmap('jet')


def create_gene_plots_per_go(data, save_name, out_dir=None, exp_data=None,
                             run_parallel=False, plot_type='plotly'):
    """ Creates a figure for each GO term in data

    Data should be a result of running calculate_enrichment.
    This function creates a plot of all proteins per term if a term is
    significant and the number of the reference set is larger than 5 and
    the total number of species measured is less than 100.


    Parameters
    ----------
    data : pandas.DataFrame
        previously ran enrichment analysis
    save_name : str
        name to save file   
    out_dir : str
        output path for file
    exp_data : magine.ExperimentalData
        data to plot
    run_parallel : bool
        To run in parallel using pathos.multiprocessing
    plot_type : str
        plotly or matplotlib
    
    Returns
    -------
    out_array : dict
        dict where keys are pointers to figure locations
    """

    if isinstance(data, str):
        data = pd.read_csv(data)
    if out_dir is not None:
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)
        if not os.path.exists(os.path.join(out_dir, 'Figures')):
            os.mkdir(os.path.join(out_dir, 'Figures'))
    data = data.copy()
    figure_locations = {}
    plots_to_create = []
    to_remove = set()
    assert plot_type == ('plotly' or 'matplotlib')
    # get list of all terms
    list_of_go_terms = data['GO_id'].unique()

    # filter data by significance and number of references
    list_of_sig_go = data[(data['ref'] >= 5)
                          &
                          (data['ref'] <= 2000)
                          &
                          (data['pvalue'] < 0.05)]['GO_id'].unique()
    if len(list_of_sig_go) == 0:
        print("No significant GO terms!!!")
        return figure_locations, to_remove
    # here we are going to iterate through all sig GO terms and create
    # a list of plots to create. For the HTML side, we need to point to
    # a location

    # create plot of genes over time
    for n, i in enumerate(list_of_go_terms):
        local_exp_data = exp_data.data.copy()
        # want to plot all species over time
        index = data['GO_id'] == i

        name = data[index]['GO_name'].unique()

        if len(name) > 0:
            name = name[0]

        # want to only plot significant species
        if i not in list_of_sig_go:
            to_remove.add(i)
            figure_locations[i] = '<a>{0}</a>'.format(name)
            continue

        gene_set = set()
        genes = data[index]['genes']
        for g in genes:
            if isinstance(g, list):
                each = g
            else:
                each = literal_eval(g)

            gene_set = {j for j in each}

        if plot_type == 'matplotlib':
            # too many genes isn't helpful on plots, so skip them
            if len(gene_set) > 100:
                figure_locations[i] = '<a>{0}</a>'.format(name)
                continue
        local_save_name = 'Figures/go_{0}_{1}'.format(i, save_name)
        if out_dir is not None:
            local_save_name = '{0}/{1}'.format(out_dir, local_save_name)

        local_save_name = local_save_name.replace(':', '')
        out_point = '<a href="{0}.html">{1}</a>'.format(local_save_name, name)
        figure_locations[i] = out_point

        title = "{0} : {1}".format(str(i), name)
        local_df = local_exp_data[
            local_exp_data[gene].isin(list(gene_set))].copy()
        p_input = (local_df, list(gene_set), local_save_name, '.', title,
                   plot_type)

        plots_to_create.append(p_input)

    # return figure_locations, to_remove

    print("Starting to create plots for each GO term")
    # just keeping this code just in case using pathos is a bad idea
    # ultimately, using matplotlib is slow.

    if run_parallel:
        st2 = time.time()
        pool = mp.Pool()
        pool.map_async(plot_list_of_genes, plots_to_create)
        # pool.map(plot_list_of_genes, plots_to_create)
        pool.close()
        pool.join()
        end2 = time.time()
        print("parallel time = {}".format(end2 - st2))
        print("Done creating plots for each GO term")

    else:
        st1 = time.time()
        for i in plots_to_create:
            plot_list_of_genes(i)
        end1 = time.time()
        print("sequential time = {}".format(end1 - st1))

    return figure_locations, to_remove


def write_table_to_html_with_figures(data, exp_data, save_name='index',
                                     out_dir=None, run_parallel=True):
    # create plots of everything
    if isinstance(data, str):
        data = pd.read_csv(data)
    # print(data.dtypes)
    # tmp = pivot_table_for_export(data)
    # print(tmp.dtypes)

    fig_dict, to_remove = create_gene_plots_per_go(
        data, save_name, out_dir, exp_data, run_parallel=run_parallel
    )

    for i in fig_dict:
        data.loc[data['GO_id'] == i, 'GO_name'] = fig_dict[i]

    data = data[~data['GO_id'].isin(to_remove)]

    tmp = pivot_table_for_export(data)

    html_out = save_name
    if out_dir is not None:
        html_out = os.path.join(out_dir, html_out)
    print("Saving to : {}".format(html_out))

    html_out = save_name + '_filter'
    if out_dir is not None:
        html_out = os.path.join(out_dir, html_out)

    ht.write_filter_table(tmp, html_out, 'MAGINE GO analysis')
    """
    items = []
    for i, row in data.iterrows():
        if i > 100:
            continue
        i = str(i)

        an_item = dict(GO_id=row['GO_id'], id_num=i,
                       enrichment_score=row['enrichment_score'],
                       pvalue=row['pvalue'],
                       genes=row['genes'],
                       n_genes=row['n_genes'],
                       )
        items.append(an_item)

    keys = ['GO_ID', 'enrichment_score', 'p-value', 'n_genes']
    html_out = enrich_template.render(header=keys, items=items)
    with open('{}.html'.format(save_name), 'w') as f:
        f.write(html_out)
    """


def plot_dataframe(exp_data, html_filename, out_dir='proteins',
                   plot_type='plotly', type_of_species='protein',
                   run_parallel=False):
    """
    Creates a plot of all proteins

    Parameters
    ----------
    exp_data : pandas.DataFrame
    html_filename : str
    out_dir: str, path
        Directory that will contain all proteins
    plot_type : str
        plotly or matplotlib output
    type_of_species : str
        proteins or metabolites
    run_parallel : bool
        create plots in parallel
    Returns
    -------

    """

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    if type_of_species == 'protein':
        idx_key = 'gene'
        plot_func = plot_list_of_genes
    elif type_of_species == 'metabolites':
        idx_key = 'compound'
        plot_func = plot_list_of_metabolites
    else:
        print('type_of_species can only be "protein" or "metabolites"')
        return
    local_data = exp_data[exp_data['species_type'] == type_of_species].copy()

    assert idx_key in local_data.dtypes,\
        '{} is not in your species_type column.\n'.format(idx_key)

    species_to_plot = local_data[idx_key].unique()

    print("Plotting {} {}".format(len(species_to_plot), type_of_species))
    # """
    figure_locations = {}
    list_of_plots = []
    for i in species_to_plot:
        save_name = re.sub('[/_.]', '', i)
        list_of_plots.append(
            (local_data, [i], save_name, out_dir, i, plot_type)
        )

        if plot_type == 'plotly':
            out_point = '<a href="{0}/{1}.html">{1}</a>'.format(out_dir,
                                                                save_name)
            figure_locations[i] = out_point
        else:
            out_point = '<a href="{0}/{1}.pdf">{1}</a>'.format(out_dir,
                                                               save_name)
            figure_locations[i] = out_point

    if run_parallel:
        st2 = time.time()
        pool = mp.Pool()
        pool.map_async(plot_func, list_of_plots)
        # pool.map(plot_list_of_genes, plots_to_create)
        pool.close()
        pool.join()
        end2 = time.time()
        print("parallel time = {}".format(end2 - st2))
        print("Done creating plots for each GO term")

    else:
        st1 = time.time()
        map(plot_func, list_of_plots)
        end1 = time.time()
        print("sequential time = {}".format(end1 - st1))

    # Place a link to the species for each key
    for i in figure_locations:
        local_data.loc[exp_data[idx_key] == i, idx_key] = figure_locations[i]
    # """

    # Pivot the pandas df to be samples vs species
    # genes_out, meta_out = pivot_tables_for_export(local_data)

    if type_of_species == 'protein':
        # output = genes_out
        cols = ['gene', 'treated_control_fold_change', 'protein',
                'p_value_group_1_and_group_2', 'time', 'data_type',
                'significant_flag',  # 'time_points',
                ]
    elif type_of_species == 'metabolites':
        # output = meta_out
        cols = ['compound',
                'treated_control_fold_change',
                'p_value_group_1_and_group_2', 'significant_flag',
                'data_type', 'time',  # 'time_points',
                ]
        if 'compound_id' in local_data.columns:
            cols.insert(2, 'compound_id')
        # output = output[['treated_control_fold_change',
        #                  'p_value_group_1_and_group_2',
        # 'data_type',
        # 'significant_flag',
        # ]]
    local_data = local_data[cols]
    # if out_dir is not None:
    #     html_filename = os.path.join(out_dir, html_filename)
    # write_single_table(local_data, html_filename, idx_key)
    ht.write_filter_table(local_data, html_filename, idx_key)


def plot_list_of_metabolites(dataframe, list_of_metab=None, save_name='test',
                             out_dir=None, title=None, plot_type='plotly',
                             image_format='pdf'):
    """

    Parameters
    ----------
    dataframe: pandas.DataFrame
        magine formatted dataframe
    list_of_metab: list
        List of genes to be plotter
    save_name: str
        Filename to be saved as
    out_dir: str
        Path for output to be saved
    title: str
        Title of plot, useful when list of genes corresponds to a GO term
    plot_type : str
        Use plotly to generate html output or matplotlib to generate pdf
    image_format : str
        pdf or png, only used if plot_type="matplotlib"

    Returns
    -------

    """
    if out_dir is not None:
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)

    if list_of_metab is None:
        dataframe, list_of_metab, save_name, out_dir, title, plot_type = dataframe

    if 'sample_id' not in dataframe.dtypes:
        dataframe['sample_id'] = dataframe['time']

    # gather x axis points
    x_points = sorted(dataframe[sample_id].unique())

    if isinstance(x_points[0], np.float):
        x_point_dict = {i: x_points[n] for n, i
                        in enumerate(x_points)}
    else:
        x_point_dict = {i: n for n, i
                        in enumerate(x_points)}

    local_df = dataframe[dataframe[meta_index].isin(list_of_metab)].copy()
    local_df = log2_normalize_df(local_df, fold_change=fold_change)

    n_plots = len(local_df[meta_index].unique())
    group = local_df.groupby(meta_index)

    color_list = [cm(1. * i / n_plots) for i in range(n_plots)]
    colors = enumerate(color_list)

    if plot_type == 'matplotlib':
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_prop_cycle(plt.cycler('color', color_list))

    plotly_list = []
    names_list = []
    total_counter = 0
    for n, m in group:
        name = n
        index_counter = 0
        x = np.array(m[sample_id])
        if len(x) < 1:
            continue
        y = np.array(m['log2fc'])
        sig_flag = np.array(m[flag])
        index = np.argsort(x)
        x = x[index]
        y = y[index]
        s_flag = sig_flag[index]

        # x values with scaled values (only changes things if non-float
        # values are used for sample_id
        x_index = np.array([x_point_dict[ind] for ind in x])

        index_counter += 1
        total_counter += 1
        # create matplotlib plot
        if plot_type == 'matplotlib':
            label = "\n".join(wrap(n, 40))
            p = ax.plot(x_index, y, '.-', label=label)
            if len(s_flag) != 0:
                color = p[0].get_color()
                ax.plot(x_index[s_flag], y[s_flag], '^', color=color)
        # create plotly plot
        elif plot_type == 'plotly':
            c = next(colors)[1]
            plotly_list.append(_create_ploty_graph(x_index, y, n, n, c))
            if len(s_flag) != 0:
                index_counter += 1
                total_counter += 1
                plotly_list.append(_create_ploty_graph(x_index[s_flag],
                                                       y[s_flag], n, n,
                                                       c,
                                                       marker='x-open-dot'))
        names_list.append([name, index_counter])

    if plot_type == 'matplotlib':
        _save_matplotlib_output(ax, save_name, out_dir, image_format,
                                x_point_dict, x_points)

    elif plot_type == 'plotly':

        _save_ploty_output(out_dir, save_name, total_counter, n_plots,
                           names_list, x_point_dict, title, x_points,
                           plotly_list)


def plot_list_of_genes(dataframe, list_of_genes=None, save_name='test',
                       out_dir=None, title=None, plot_type='plotly',
                       image_format='pdf'):
    """

    Parameters
    ----------
    dataframe: pandas.DataFrame
        magine formatted dataframe
    list_of_genes: list
        List of genes to be plotter
    save_name: str
        Filename to be saved as
    out_dir: str
        Path for output to be saved
    title: str
        Title of plot, useful when list of genes corresponds to a GO term
    plot_type : str
        Use plotly to generate html output or matplotlib to generate pdf
    image_format : str
        pdf or png, only used if plot_type="matplotlib"

    Returns
    -------

    """

    if list_of_genes is None:
        dataframe, list_of_genes, save_name, out_dir, title, plot_type = dataframe

    ldf = dataframe.copy(deep=True)
    if out_dir is not None:
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)

    if 'sample_id' not in ldf.dtypes:
        ldf['sample_id'] = ldf['time']

    # gather x axis points
    x_points = sorted(ldf[sample_id].unique())
    if len(x_points) == 0:
        return
    if isinstance(x_points[0], np.float):
        x_point_dict = {i: x_points[n] for n, i
                        in enumerate(x_points)}
    else:
        x_point_dict = {i: n for n, i
                        in enumerate(x_points)}

    local_df = ldf[ldf[gene].isin(list_of_genes)].copy(deep=True)
    local_df = log2_normalize_df(local_df, fold_change=fold_change)

    n_plots = len(local_df[gene].unique())
    num_colors = len(local_df[protein].unique())
    color_list = [cm(1. * i / num_colors) for i in range(num_colors)]

    if plot_type == 'matplotlib':
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_prop_cycle(plt.cycler('color', color_list))

    colors = enumerate(color_list)

    plotly_list = []
    names_list = []
    total_counter = 0
    group = local_df.groupby(gene)
    for i, j in group:
        name = i
        group2 = j.groupby(protein)
        index_counter = 0
        for n, m in group2:

            x = np.array(m[sample_id])
            if len(x) < 1:
                continue
            y = np.array(m['log2fc'])
            sig_flag = np.array(m[flag])
            index = np.argsort(x)
            x = x[index]
            y = y[index]
            s_flag = sig_flag[index]

            # x values with scaled values (only changes things if non-float
            # values are used for sample_id
            x_index = np.array([x_point_dict[ind] for ind in x])

            index_counter += 1
            total_counter += 1
            # create matplotlib plot
            if plot_type == 'matplotlib':
                label = "\n".join(wrap(n, 40))
                p = ax.plot(x_index, y, '.-', label=label)
                if len(s_flag) != 0:
                    color = p[0].get_color()
                    ax.plot(x_index[s_flag], y[s_flag], '^', color=color)
            # create plotly plot
            elif plot_type == 'plotly':
                c = next(colors)[1]
                plotly_list.append(_create_ploty_graph(x_index, y, n, n, c))
                if len(s_flag) != 0:
                    index_counter += 1
                    total_counter += 1
                    plotly_list.append(_create_ploty_graph(x_index[s_flag],
                                                           y[s_flag], n, n,
                                                           c,
                                                           marker='x-open-dot'))
        names_list.append([name, index_counter])

    if plot_type == 'matplotlib':
        _save_matplotlib_output(ax, save_name, out_dir, image_format,
                                x_point_dict, x_points)

    elif plot_type == 'plotly':
        _save_ploty_output(out_dir, save_name, total_counter, n_plots,
                           names_list, x_point_dict, title, x_points,
                           plotly_list)


def _save_matplotlib_output(ax, save_name, out_dir, image_format, x_point_dict,
                            x_points, ):
    ax.set_xlim(min(x_point_dict.values()) - 2, max(x_point_dict.values()) + 2)
    ax.set_xticks(sorted(x_point_dict.values()))
    ax.set_xticklabels(x_points, rotation=90)
    plt.ylabel('log$_2$ Fold Change')

    plt.axhline(y=np.log2(1.5), linestyle='--')
    plt.axhline(y=-np.log2(1.5), linestyle='--')

    handles, labels = ax.get_legend_handles_labels()
    lgd = ax.legend(handles, labels, loc='best',
                    bbox_to_anchor=(1.01, 1.0))

    tmp_savename = "{}.{}".format(save_name, image_format)
    if out_dir is not None:
        tmp_savename = os.path.join(out_dir, tmp_savename)

    plt.savefig(tmp_savename, bbox_extra_artists=(lgd,),
                bbox_inches='tight')


def _save_ploty_output(out_dir, save_name, total_counter, n_plots, names_list,
                       x_point_dict, title, x_points, plotly_list):
    from magine.html_templates.html_tools import format_ploty
    true_list = [True] * total_counter
    scroll_list = [dict(args=['visible', true_list],
                        label='All',
                        method='restyle')]

    prev = 0
    # making all false except group defined by protein name
    for i in range(n_plots):
        t_row = [False] * total_counter
        for j in range(prev, prev + names_list[i][1]):
            t_row[j] = True
        prev += names_list[i][1]
        scroll = dict(args=['visible', t_row],
                      label=names_list[i][0], method='restyle')
        scroll_list.append(scroll)

    update_menu = list([dict(x=-0.05,
                             y=1,
                             yanchor='top',
                             buttons=scroll_list, )])
    ticks = np.sort(list(x_point_dict.values()))
    min_tick = np.min(ticks)
    max_tick = np.max(ticks)
    layout = plotly_graph.Layout(
        title=title,
        showlegend=True,
        xaxis=dict(title='Sample index',
                   range=[min_tick, max_tick],
                   showticklabels=True,
                   ticktext=x_points,
                   tickmode='array',
                   tickvals=ticks,
                   ),
        yaxis=dict(title='log2fc'),
        hovermode="closest",
        updatemenus=update_menu
    )

    fig = plotly_graph.Figure(data=plotly_list, layout=layout)
    tmp_savename = "{}.html".format(save_name)
    if out_dir is not None:
        tmp_savename = os.path.join(out_dir, tmp_savename)

    x = plot(fig, filename=tmp_savename, auto_open=False,
             include_plotlyjs=False, output_type='div')
    format_ploty(x, tmp_savename)


def _create_ploty_graph(x, y, label, enum, color, marker='circle'):
    """
    Creates a single scatter plot
    Parameters
    ----------
    x : list_like
    y : list_like
    label : str
    enum : int
    color : str
    marker : str

    Returns
    -------

    """
    l_color = 'rgba({},{},{},1.)'.format(color[0], color[1], color[2])
    if marker != 'circle':
        mode = 'markers'
        show = False
        size = 12
    else:
        mode = 'lines+markers'
        show = True
        size = 8
    legendgroup = 'group_{}'.format(enum)

    g = plotly_graph.Scatter(
            x=x,
            y=y,
            hoveron='text',
            name=label,
            visible=True,
            mode=mode,
            legendgroup=legendgroup,
            showlegend=show,
            line=dict(color=l_color),
            marker=dict(symbol=marker,
                        size=size,
                        color=l_color),
    )
    return g
