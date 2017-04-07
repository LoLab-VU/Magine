import pandas as pd
import time
import pathos.multiprocessing as mp
from ast import literal_eval
import os
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from textwrap import wrap
from plotly.offline import plot
import plotly
import sys
import plotly.graph_objs as plotly_graph
import plotly.tools as tls

gene = 'gene'
protein = 'protein'
metabolites = 'metabolites'
species_type = 'species_type'
sample_id = 'time'
fold_change = 'treated_control_fold_change'
flag = 'significant_flag'
tls.set_credentials_file(username='james.ch.pino',
                         api_key='BnUcJSpmPcMKZg0yEFaL')


def create_gene_plots_per_go(data, save_name, out_dir, exp_data):
    """ Creates a figure for each GO term in data

    Data should be a result of running create_enrichment_array.
    This function creates a plot of all proteins per term if a term is
    significant and the number of the reference set is larger than 5 and
    the total number of species measured is less than 50.



    Parameters
    ----------
    data : pandas.DataFrame, optional
        previously ran enrichment analysis

    Returns
    -------
    out_array : dict
        dict where keys are pointers to figure locations
    """

    if isinstance(data, str):
        data = pd.read_csv(data)
    # get list of all terms
    list_of_go_terms = data['GO_id'].unique()

    # filter data by significance and number of references
    list_of_sig_go = data[(data['ref'] >= 5)
                          &
                          (data['pvalue'] < 0.05)]['GO_id'].unique()

    # here we are going to iterate through all sig GO terms and create
    # a list of plots to create. For the HTML side, we need to point to
    # a location
    figure_locations = {}
    plots_to_create = []
    to_remove = set()
    # create plot of genes over time
    for n, i in enumerate(list_of_go_terms):

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
            each = literal_eval(g)
            for j in each:
                gene_set.add(j)
        # too many genes isn't helpful on plots, so skip them
        if len(gene_set) > 50:
            figure_locations[i] = '<a>{0}</a>'.format(name)
            continue

        local_save_name = '{0}/Figures/go_{1}_{2}'.format(out_dir, i,
                                                          save_name)
        local_save_name = local_save_name.replace(':', '')
        title = "{0} : {1}".format(str(i), name)
        local_df = exp_data.data[exp_data.data[gene].isin(list(gene_set))]
        plots_to_create.append(
                (local_df, list(gene_set), local_save_name, '.', title, True,
                 True))
        # out_point = '<a href="Figures/go_{0}_{1}.pdf">{2} ({0})</a>'
        out_point = '<a href="Figures/go_{0}_{1}.html">{2} ({0})</a>'
        out_point = out_point.format(i,
                                     save_name,
                                     name).replace(':', '')
        figure_locations[i] = out_point
    return figure_locations, to_remove
    print(sys.getsizeof(plots_to_create))
    print("Starting to create plots for each GO term")
    # just keeping this code just in case using pathos is a bad idea
    # ultimately, using matplotlib is slow.
    run_seq = True
    run_seq = False
    run_par = False
    run_par = True

    if run_seq:
        st1 = time.time()
        for i in plots_to_create:
            # exp_data.plot_list_of_genes_plotly(i)
            plot_list_of_genes2(i)
        end1 = time.time()
        print("sequential time = {}".format(end1 - st1))

    if run_par:
        st2 = time.time()
        pool = mp.Pool(4)
        # pool.map(exp_data.plot_list_of_genes, plots_to_create)
        pool.map(plot_list_of_genes2, plots_to_create)
        pool.close()
        pool.join()
        end2 = time.time()
        print("parallel time = {}".format(end2 - st2))
    print("Done creating plots for each GO term")

    return figure_locations, to_remove


# @profile
def plot_list_of_genes2(dataframe, list_of_genes=None, save_name='test',
                        out_dir='.',
                        title=None, plot_all_x=False, log_scale=False,
                        plot_type='plotly'):
    """

    Parameters
    ----------
    list_of_genes: list
        List of genes to be plotter
    save_name: str
        Filename to be saved as
    out_dir: str
        Path for output to be saved
    title: str
        Title of plot, useful when list of genes corresponds to a GO term
    plot_all_x: bool
        Used if data samples is of time. This ensures all plots have same
        x axis.

    Returns
    -------

    """
    plotly.plotly.sign_in(username='james.ch.pino',
                          api_key='BnUcJSpmPcMKZg0yEFaL')
    tls.set_credentials_file(username='james.ch.pino',
                             api_key='BnUcJSpmPcMKZg0yEFaL')
    if os.path.exists(out_dir):
        pass
    else:
        os.mkdir(out_dir)

    if list_of_genes is None:
        dataframe, list_of_genes, save_name, out_dir, title, plot_all_x, log_scale = dataframe

    x_points = sorted(dataframe[sample_id].unique())

    if isinstance(x_points[0], np.float):
        x_point_dict = {i: x_points[n] for n, i
                        in enumerate(x_points)}
    else:
        x_point_dict = {i: 2 ** (n + 1) for n, i
                        in enumerate(x_points)}

    local_df = dataframe[dataframe[gene].isin(list_of_genes)]

    n_genes = len(local_df[gene].unique())
    group = local_df.groupby(gene)

    cm = plt.get_cmap('jet')
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
    for i, j in group:
        name = i

        group2 = j.groupby(protein)
        index_counter = 0
        for n, m in group2:

            x_index = []
            x = np.array(m[sample_id])
            if len(x) < 1:
                continue
            y = np.array(m[fold_change])
            sig_flag = np.array(m[flag])
            index = np.argsort(x)
            x = x[index]
            y = y[index]
            s_flag = sig_flag[index]

            # x values with scaled values (only changes things if non-float
            # values are used for sample_id
            for ind in x:
                x_index.append(x_point_dict[ind])
            x_index = np.array(x_index)

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
                c = colors.next()[1]
                plotly_list.append(create_ploty_graph(x_index, y, n, n, c))
                if len(s_flag) != 0:
                    index_counter += 1
                    total_counter += 1
                    plotly_list.append(create_ploty_graph(x_index[s_flag],
                                                          y[s_flag], n, n,
                                                          c,
                                                          marker='x-open-dot'))
        names_list.append([name, index_counter])
    if plot_type == 'matplotlib':
        ax.set_yscale('symlog', basey=2)
        plt.xlim(min(x_point_dict.values()) - 2,
                 max(x_point_dict.values()) + 2)
        # if log_scale:
        #     ax.set_xscale('log', basex=2)
        ax.set_xticks(sorted(x_point_dict.values()))
        ax.set_xticklabels(x_points)
        plt.ylabel('log$_2$ Fold Change')
        locs, labels = plt.xticks()
        plt.setp(labels, rotation=90)
        plt.axhline(y=np.log2(1.5), linestyle='--')
        plt.axhline(y=-np.log2(1.5), linestyle='--')

        handles, labels = ax.get_legend_handles_labels()
        lgd = ax.legend(handles, labels, loc='best',
                        bbox_to_anchor=(1.01, 1.0))
        tmp_savename = os.path.join(out_dir, "{}.pdf".format(save_name))
        # print("Saving {}".format(tmp_savename))
        plt.savefig(tmp_savename, bbox_extra_artists=(lgd,),
                    bbox_inches='tight')
    elif plot_type == 'plotly':
        true_list = [True] * total_counter
        scroll_list = [
            dict(args=['visible', true_list],
                 label='All', method='update')]
        prev = 0
        # print(names_list)
        # print(total_counter)
        for i in range(n_genes):
            t_row = [False] * total_counter
            # print(names_list[i])
            for j in range(prev, prev + names_list[i][1]):
                t_row[j] = True
            prev += names_list[i][1]
            scroll = dict(args=['visible', t_row],
                          label=names_list[i][0], method='update')
            scroll_list.append(scroll)
        # print(num_colors)
        # for i in scroll_list:
        #     print(i)
        update_menu = list([dict(x=-0.05,
                                 y=1,
                                 yanchor='top',
                                 buttons=scroll_list, )])
        layout = plotly_graph.Layout(
                title=title,
                showlegend=True,
                xaxis=dict(title='Sample index'),
                hovermode="closest",
                updatemenus=update_menu)

        fig = plotly_graph.Figure(data=plotly_list, layout=layout)
        s_name = '{}.html'.format(save_name)
        # print("Saving {}".format(s_name))
        plot(fig, filename=s_name, auto_open=False)


def create_ploty_graph(x, y, label, enum, color, marker='circle'):
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

    g = plotly_graph.Scatter(x=x, y=y,
                             hoveron='text', name=label,
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