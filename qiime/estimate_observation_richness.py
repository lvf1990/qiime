#!/usr/bin/env python
from __future__ import division

__author__ = "Jai Ram Rideout"
__copyright__ = "Copyright 2013, The QIIME Project"
__credits__ = ["Jai Ram Rideout"]
__license__ = "GPL"
__version__ = "1.6.0-dev"
__maintainer__ = "Jai Ram Rideout"
__email__ = "jai.rideout@gmail.com"
__status__ = "Development"

"""Contains functionality to estimate the observation richness of samples."""

from math import factorial
from numpy import ceil

class EmptyTableError(Exception):
    pass

class EmptySampleError(Exception):
    pass

class AbstractObservationRichnessEstimator(object):
    def __init__(self, biom_table, FullRichnessEstimator):
        if biom_table.isEmpty():
            raise EmptyTableError("The input BIOM table cannot be empty.")
        self._biom_table = biom_table

        for c in self.getTotalIndividualCounts():
            if c < 1:
                raise EmptySampleError("Encountered a sample without any "
                                       "recorded observations.")

        self.FullRichnessEstimator = FullRichnessEstimator

    def getSampleCount(self):
        return len(self._biom_table.SampleIds)

    def getTotalIndividualCounts(self):
        return [int(e) for e in self._biom_table.sum(axis='sample')]

    def getObservationCounts(self):
        return [(e > 0).sum(0) for e in self._biom_table.iterSampleData()]

    def getAbundanceFrequencyCounts(self):
        for samp_data, num_individuals in zip(
                self._biom_table.iterSampleData(),
                self.getTotalIndividualCounts()):
            samp_abundance_freq_count = []

            for i in range(1, num_individuals + 1):
                samp_abundance_freq_count.append((samp_data == i).sum(0))
            yield samp_abundance_freq_count

    def __call__(self):
        raise NotImplementedError("Subclasses must implement __call__.")


class ObservationRichnessInterpolator(AbstractObservationRichnessEstimator):
    def __init__(self, biom_table, FullRichnessEstimator):
        super(ObservationRichnessInterpolator, self).__init__(biom_table,
                FullRichnessEstimator)

    def __call__(self, point_count=40):
        per_sample_results = []

        for samp_data, num_obs, n, abundance_freqs in zip(
                self._biom_table.iterSampleData(),
                self.getObservationCounts(),
                self.getTotalIndividualCounts(),
                self.getAbundanceFrequencyCounts()):
            samp_data = samp_data[samp_data > 0]
            step_size = int(ceil(n / (point_count - 1)))
            sizes = range(1, n, step_size)
            sizes.append(n)

            size_results = []
            # size <= n
            for size in sizes:
                # Equation 4 in Colwell 2012
                curr_sum = 0

                for k in range(1, n + 1):
                    if k <= (n - size):
                        alpha_km = ((factorial(n - k) * factorial(n - size)) /
                                    (factorial(n) * factorial(n - k - size)))
                    else:
                        alpha_km = 0

                    # k is 1..n while abundance_freqs idxs are 0..n-1.
                    curr_sum += alpha_km * abundance_freqs[k - 1]

                size_results.append((size, num_obs - curr_sum))

            per_sample_results.append(size_results)

        return per_sample_results


class AbstractFullRichnessEstimator(object):
    def estimateFullRichness(self, abundance_frequency_counts,
                             observation_count):
        # S_est = S_obs + f_hat_0
        return observation_count + self.estimateUnobservedObservationCount(
                abundance_frequency_counts)

    def estimateUnobservedObservationCount(self, abundance_frequency_counts):
        raise NotImplementedError("Subclasses must implement "
                                  "estimateUnobservedObservationCount.")


class Chao1FullRichnessEstimator(AbstractFullRichnessEstimator):
    def estimateUnobservedObservationCount(self, abundance_frequency_counts):
        # Based on equation 15a and 15b of Colwell 2012.
        f1 = abundance_frequency_counts[0]
        f2 = abundance_frequency_counts[1]

        if f2 > 0:
            estimated_unobserved_count = f1**2 / (2 * f2)
        elif f2 == 0:
            estimated_unobserved_count = (f1 * (f1 - 1)) / (2 * (f2 + 1))
        else:
            raise ValueError("Encountered a negative f2 value (%d), which is "
                             "invalid." % f2)

        return estimated_unobserved_count
