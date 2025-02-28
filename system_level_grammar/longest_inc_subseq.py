from bisect import bisect_right

def longest_increasing_subsequence(nums):
    if not nums:
        return []

    lis = []
    prev_indices = [-1] * len(nums)
    dp = []

    for i, num in enumerate(nums):
        pos = bisect_right(dp, num)

        if pos == len(dp):
            dp.append(num)
        else:
            dp[pos] = num

        if pos > 0:
            prev_indices[i] = lis[pos-1]

        if pos == len(lis):
            lis.append(i)
        else:
            lis[pos] = i

    length_of_lis = len(dp)
    lis_sequence = [0] * length_of_lis
    k = lis[-1]

    for j in range(length_of_lis-1, -1, -1):
        lis_sequence[j] = nums[k]
        k = prev_indices[k]

    return lis_sequence

def max_longest_increasing_subsequence(nums):
    if not nums:
        return []

    n = len(nums)
    dp = [1] * n
    sums = nums[:]
    predecessors = [-1] * n

    for i in range(1, n):
        for j in range(i):
            if nums[i] > nums[j]:
                if dp[j] + 1 > dp[i]:
                    dp[i] = dp[j] + 1
                    sums[i] = sums[j] + nums[i]
                    predecessors[i] = j
                elif dp[j] + 1 == dp[i] and sums[j] + nums[i] > sums[i]:
                    sums[i] = sums[j] + nums[i]
                    predecessors[i] = j

    max_len = max(dp)
    max_sum = float('-inf')
    max_index = -1
    for i in range(n):
        if dp[i] == max_len and sums[i] > max_sum:
            max_sum = sums[i]
            max_index = i

    lis = []
    while max_index != -1:
        lis.append(nums[max_index])
        max_index = predecessors[max_index]

    return lis[::-1]