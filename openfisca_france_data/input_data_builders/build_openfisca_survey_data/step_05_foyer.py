#! /usr/bin/env python
# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014, 2015 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


# OpenFisca
# Retreives data from erf foyer
# Creates sif and foyer_aggr


from __future__ import division


import gc
import logging

import numpy
from pandas import concat, DataFrame, Series
import re


from openfisca_survey_manager.surveys import SurveyCollection
from openfisca_france_data.input_data_builders.build_openfisca_survey_data import save_temp, show_temp
from openfisca_france_data.input_data_builders.build_openfisca_survey_data.utils import print_id

log = logging.getLogger(__name__)


def sif(year = 2006):
    erfs_survey_collection = SurveyCollection.load(collection='erfs')
    data = erfs_survey_collection.surveys['erfs_{}'.format(year)]

    log.info("05_foyer: extraction des données foyer")
    ## TODO Comment choisir le rfr n -2 pour éxonération de TH ?
    ## mnrvka  Revenu TH n-2
    ## mnrvkh  revenu TH (revenu fiscal de référence)
    #
    ## On récupère les variables du code sif
    #vars <- c("noindiv", 'sif', "nbptr", "mnrvka")
    vars = ["noindiv", 'sif', "nbptr", "mnrvka", "rbg", "tsrvbg"]
    sif = data.get_values(variables = vars, table = "foyer")
    #sif$statmarit <- 0
    sif['statmarit'] = 0

    if year == 2009:
        old_sif = sif['sif'][sif['noindiv'] == 901803201].copy()
        new_sif = old_sif.str[0:59] + old_sif.str[60:] + "0"
        sif['sif'][sif['noindiv'] == 901803201] = new_sif.values
        old_sif = sif['sif'][sif['noindiv'] == 900872201]
        new_sif = old_sif.str[0:58] + " " + old_sif.str[58:]
        sif['sif'][sif['noindiv'] == 900872201] = new_sif.values
        del old_sif, new_sif

    sif["rbg"] = sif["rbg"] * ((sif["tsrvbg"] == '+').astype(int) - (sif["tsrvbg"] == '-').astype(int))
    sif["stamar"] = sif.sif.str[4:5]

    # Converting marital status
    statmarit_dict = {"M": 1, "C": 2, "D": 3, "V": 4, "O": 5}
    for key, val in statmarit_dict.iteritems():
        sif["statmarit"][sif.stamar == key] = val

    sif["birthvous"] = sif.sif.str[5:9]
    sif["birthconj"] = sif.sif.str[10:14]
    sif["caseE"] = sif.sif.str[15:16] == "E"
    sif["caseF"] = sif.sif.str[16:17] == "F"
    sif["caseG"] = sif.sif.str[17:18] == "G"
    sif["caseK"] = sif.sif.str[18:19] == "K"

    d = 0
    if year in [2006, 2007]:
        sif["caseL"] = sif.sif.str[19:20] == "L"
        sif["caseP"] = sif.sif.str[20:21] == "P"
        sif["caseS"] = sif.sif.str[21:22] == "S"
        sif["caseW"] = sif.sif.str[22:23] == "W"
        sif["caseN"] = sif.sif.str[23:24] == "N"
        sif["caseH"] = sif.sif.str[24:28]
        sif["caseT"] = sif.sif.str[28:29] == "T"

    if year in [2008]:
        d = - 1  # fin de la case L
        sif["caseP"] = sif.sif.str[20 + d: 21 + d] == "P"
        sif["caseS"] = sif.sif.str[21 + d: 22 + d] == "S"
        sif["caseW"] = sif.sif.str[22 + d: 23 + d] == "W"
        sif["caseN"] = sif.sif.str[23 + d: 24 + d] == "N"
        sif["caseH"] = sif.sif.str[24 + d: 28 + d]
        sif["caseT"] = sif.sif.str[28 + d: 29 + d] == "T"

    if year in [2009]:
        sif["caseL"] = sif.sif.str[19: 20] == "L"
        sif["caseP"] = sif.sif.str[20: 21] == "P"
        sif["caseS"] = sif.sif.str[21: 22] == "S"
        sif["caseW"] = sif.sif.str[22: 23] == "W"
        sif["caseN"] = sif.sif.str[23: 24] == "N"
        # caseH en moins par rapport à 2008 (mais case en L en plus)
        # donc décalage par rapport à 2006
        d = -4
        sif["caseT"] = sif.sif.str[28 + d: 29 + d] == "T"

    sif["caseX"] = sif.sif.str[33 + d: 34 + d] == "X"
    sif["dateX"] = sif.sif.str[34 + d: 42 + d]
    sif["caseY"] = sif.sif.str[42 + d: 43 + d] == "Y"
    sif["dateY"] = sif.sif.str[43 + d: 51 + d]
    sif["caseZ"] = sif.sif.str[51 + d: 53 + d] == "Z"
    sif["dateZ"] = sif.sif.str[52 + d: 60 + d]
    sif["causeXYZ"] = sif.sif.str[60 + d: 61 + d]

    # TODO: convert dateXYZ to appropriate date in pandas
    # print sif["dateY"].unique()

    sif["nbptr"] = sif.nbptr.values / 100
    sif["rfr_n_2"] = sif.mnrvka.values

    sif["nbF"] = sif.sif.str[64 + d: 66 + d]
    sif["nbG"] = sif.sif.str[67 + d: 69 + d]
    sif["nbR"] = sif.sif.str[70 + d: 72 + d]
    sif["nbJ"] = sif.sif.str[73 + d: 75 + d]
    sif["nbN"] = sif.sif.str[76 + d: 78 + d]
    sif["nbH"] = sif.sif.str[79 + d: 81 + d]
    sif["nbI"] = sif.sif.str[82 + d: 84 + d]

    if (year != 2009):
        sif["nbP"] = sif.sif.str[85 + d: 87 + d]

    del sif["sif"], sif["stamar"]

    log.info("Number of individuals: {}".format(len(sif.noindiv)))
    log.info("Number of distinct individuals: {}".format(len(sif.noindiv.value_counts())))

    sif_drop_duplicated = sif.drop_duplicates("noindiv")
    assert len(sif["noindiv"].value_counts()) == len(sif_drop_duplicated["noindiv"]), \
        "Number of distinct individuals after removing duplicates is not correct"

    log.info(u"Saving sif")
    save_temp(sif, name = "sif", year = year)
    del sif
    gc.collect()


def foyer_all(year = 2006):

    ## On ajoute les cases de la déclaration
    erfs_survey_collection = SurveyCollection.load(collection='erfs')
    data = erfs_survey_collection.surveys['erfs_{}'.format(year)]
    foyer_all = data.get_values(table = "foyer")
    ## on ne garde que les cases de la déclaration ('fxzz')
    vars = foyer_all.columns
    regex = re.compile("^f[0-9]")
    vars = [x for x in vars if regex.match(x)]

    foyer = foyer_all[vars + ["noindiv"]]
    del foyer_all
    gc.collect()

    ## On aggrège les déclarations dans le cas où un individu a fait plusieurs déclarations
    foyer = foyer.groupby("noindiv", as_index=False).aggregate(numpy.sum)
    print_id(foyer)

    ## On récupère les variables individualisables
    var_dict = {
        'sali': ['f1aj', 'f1bj', 'f1cj', 'f1dj', 'f1ej'],
        'choi': ['f1ap', 'f1bp', 'f1cp', 'f1dp', 'f1ep'],
        'fra': ['f1ak', 'f1bk', 'f1ck', 'f1dk', 'f1ek'],
        'cho_ld': ['f1ai', 'f1bi', 'f1ci', 'f1di', 'f1ei'],
        'ppe_tp_sa': ['f1ax', 'f1bx', 'f1cx', 'f1dx', 'f1qx'],
        'ppe_du_sa': ['f1av', 'f1bv', 'f1cv', 'f1dv', 'f1qv'],
        'rsti': ['f1as', 'f1bs', 'f1cs', 'f1ds', 'f1es'],
        'alr': ['f1ao', 'f1bo', 'f1co', 'f1do', 'f1eo'],
        'f1tv': ['f1tv', 'f1uv'],
        'f1tw': ['f1tw', 'f1uw'],
        'f1tx': ['f1tx', 'f1ux'],
        'ppe_tp_ns': ['f5nw', 'f5ow', 'f5pw'],
        'ppe_du_ns': ['f5nv', 'f5ov', 'f5pv'],
        'frag_exon': ['f5hn', 'f5in', 'f5jn'],
        'frag_impo': ['f5ho', 'f5io', 'f5jo'],
        'arag_exon': ['f5hb', 'f5ib', 'f5jb'],
        'arag_impg': ['f5hc', 'f5ic', 'f5jc'],
        'arag_defi': ['f5hf', 'f5if', 'f5jf'],
        'nrag_exon': ['f5hh', 'f5ih', 'f5jh'],
        'nrag_impg': ['f5hi', 'f5ii', 'f5ji'],
        'nrag_defi': ['f5hl', 'f5il', 'f5jl'],
        'nrag_ajag': ['f5hm', 'f5im', 'f5jm'],
        'mbic_exon': ['f5kn', 'f5ln', 'f5mn'],
        'abic_exon': ['f5kb', 'f5lb', 'f5mb'],
        'nbic_exon': ['f5kh', 'f5lh', 'f5mh'],
        'mbic_impv': ['f5ko', 'f5lo', 'f5mo'],
        'mbic_imps': ['f5kp', 'f5lp', 'f5mp'],
        'abic_impn': ['f5kc', 'f5lc', 'f5mc'],
        'abic_imps': ['f5kd', 'f5ld', 'f5md'],
        'nbic_impn': ['f5ki', 'f5li', 'f5mi'],
        'nbic_imps': ['f5kj', 'f5lj', 'f5mj'],
        'abic_defn': ['f5kf', 'f5lf', 'f5mf'],
        'abic_defs': ['f5kg', 'f5lg', 'f5mg'],
        'nbic_defn': ['f5kl', 'f5ll', 'f5ml'],
        'nbic_defs': ['f5km', 'f5lm', 'f5mm'],
        'nbic_apch': ['f5ks', 'f5ls', 'f5ms'],
        'macc_exon': ['f5nn', 'f5on', 'f5pn'],
        'aacc_exon': ['f5nb', 'f5ob', 'f5pb'],
        'nacc_exon': ['f5nh', 'f5oh', 'f5ph'],
        'macc_impv': ['f5no', 'f5oo', 'f5po'],
        'macc_imps': ['f5np', 'f5op', 'f5pp'],
        'aacc_impn': ['f5nc', 'f5oc', 'f5pc'],
        'aacc_imps': ['f5nd', 'f5od', 'f5pd'],
        'aacc_defn': ['f5nf', 'f5of', 'f5pf'],
        'aacc_defs': ['f5ng', 'f5og', 'f5pg'],
        'nacc_impn': ['f5ni', 'f5oi', 'f5pi'],
        'nacc_imps': ['f5nj', 'f5oj', 'f5pj'],
        'nacc_defn': ['f5nl', 'f5ol', 'f5pl'],
        'nacc_defs': ['f5nm', 'f5om', 'f5pm'],
        'mncn_impo': ['f5ku', 'f5lu', 'f5mu'],
        'cncn_bene': ['f5sn', 'f5ns', 'f5os'],
        'cncn_defi': ['f5sp', 'f5nu', 'f5ou', 'f5sr'], # TODO: check
        'mbnc_exon': ['f5hp', 'f5ip', 'f5jp'],
        'abnc_exon': ['f5qb', 'f5rb', 'f5sb'],
        'nbnc_exon': ['f5qh', 'f5rh', 'f5sh'],
        'mbnc_impo': ['f5hq', 'f5iq', 'f5jq'],
        'abnc_impo': ['f5qc', 'f5rc', 'f5sc'],
        'abnc_defi': ['f5qe', 'f5re', 'f5se'],
        'nbnc_impo': ['f5qi', 'f5ri', 'f5si'],
        'nbnc_defi': ['f5qk', 'f5rk', 'f5sk'],
#      'ebic_impv' : ['f5ta','f5ua', 'f5va'],
#      'ebic_imps' : ['f5tb','f5ub', 'f5vb'],
        'mbic_mvct': ['f5hu'],
        'macc_mvct': ['f5iu'],
        'mncn_mvct': ['f5ju'],
        'mbnc_mvct': ['f5kz'],
        'frag_pvct': ['f5hw', 'f5iw', 'f5jw'],
        'mbic_pvct': ['f5kx', 'f5lx', 'f5mx'],
        'macc_pvct': ['f5nx', 'f5ox', 'f5px'],
        'mbnc_pvct': ['f5hv', 'f5iv', 'f5jv'],
        'mncn_pvct': ['f5ky', 'f5ly', 'f5my'],
        'mbic_mvlt': ['f5kr', 'f5lr', 'f5mr'],
        'macc_mvlt': ['f5nr', 'f5or', 'f5pr'],
        'mncn_mvlt': ['f5kw', 'f5lw', 'f5mw'],
        'mbnc_mvlt': ['f5hs', 'f5is', 'f5js'],
        'frag_pvce': ['f5hx', 'f5ix', 'f5jx'],
        'arag_pvce': ['f5he', 'f5ie', 'f5je'],
        'nrag_pvce': ['f5hk', 'f5lk', 'f5jk'],
        'mbic_pvce': ['f5kq', 'f5lq', 'f5mq'],
        'abic_pvce': ['f5ke', 'f5le', 'f5me'],
        'nbic_pvce': ['f5kk', 'f5ik', 'f5mk'],
        'macc_pvce': ['f5nq', 'f5oq', 'f5pq'],
        'aacc_pvce': ['f5ne', 'f5oe', 'f5pe'],
        'nacc_pvce': ['f5nk', 'f5ok', 'f5pk'],
        'mncn_pvce': ['f5kv', 'f5lv', 'f5mv'],
        'cncn_pvce': ['f5so', 'f5nt', 'f5ot'],
        'mbnc_pvce': ['f5hr', 'f5ir', 'f5jr'],
        'abnc_pvce': ['f5qd', 'f5rd', 'f5sd'],
        'nbnc_pvce': ['f5qj', 'f5rj', 'f5sj'],
        'demenage': ['f1ar', 'f1br', 'f1cr', 'f1dr', 'f1er']}  # (déménagement) uniquement en 2006

    vars_sets = [set(var_list) for var_list in var_dict.values()]
    eligible_vars = (set().union(*vars_sets)).intersection( set(list(foyer.columns)))

    log.info(
        u"From {} variables, we keep {} eligibles variables".format(
            len(set().union(*vars_sets)),
            len(eligible_vars),
            )
        )

    qui = ['vous', 'conj', 'pac1', 'pac2', 'pac3']
    err = 0
    err_vars = {}

    foy_ind = DataFrame()
    for individual_var, foyer_vars in var_dict.iteritems():
        try:
            selection = foyer[foyer_vars + ["noindiv"]].copy()
        except KeyError:
            # Testing if at least one variable of foyers_vars is in the eligible list
            presence = [x in eligible_vars for x in foyer_vars]
            if not any(presence):
                log.info("{} is not present".format(individual_var))
                continue
            else:
                # Shrink the list
                foyer_vars_cleaned = [var for var, present in zip(foyer_vars, presence) if present is True]
                selection = foyer[foyer_vars_cleaned + ["noindiv"]].copy()

        # Reshape the dataframe
        selection.rename(columns=dict(zip(foyer_vars, qui)), inplace = True)
        selection.set_index("noindiv", inplace = True)
        selection.columns.name = "quifoy"

        selection = selection.stack()
        selection.name = individual_var
        selection = selection.reset_index()  # A Series cannot see its index resetted to produce a DataFrame
        selection = selection.set_index(["quifoy", "noindiv"])
        selection = selection[selection[individual_var] != 0].copy()

        if len(foy_ind) == 0:
            foy_ind = selection
        else:
            foy_ind = concat([foy_ind, selection], axis = 1, join = 'outer')

    foy_ind.reset_index(inplace=True)

    ind_vars_to_remove = Series(list(eligible_vars))
    save_temp(ind_vars_to_remove, name='ind_vars_to_remove', year=year)
    foy_ind.rename(columns = {"noindiv": "idfoy"}, inplace = True)

    print_id(foy_ind)
    foy_ind['quifoy'][foy_ind.quifoy == 'vous'] = 0
    foy_ind['quifoy'][foy_ind.quifoy == 'conj'] = 1
    foy_ind['quifoy'][foy_ind.quifoy == 'pac1'] = 2
    foy_ind['quifoy'][foy_ind.quifoy == 'pac2'] = 3
    foy_ind['quifoy'][foy_ind.quifoy == 'pac3'] = 4

    assert foy_ind.quifoy .isin(range(5)).all(), 'présence de valeurs aberrantes dans quifoy'

    log.info('saving foy_ind')
    print_id(foy_ind)
    save_temp(foy_ind, name = "foy_ind", year = year)
    show_temp()
    return


if __name__ == '__main__':
    year = 2006
    sif(year=year)
    foyer_all(year=year)
    log.info(u"étape 05 foyer terminée")