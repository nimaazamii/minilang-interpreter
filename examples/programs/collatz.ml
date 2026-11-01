# start below 3000 with the longest Collatz chain
fn chain_length(n) {
    let steps = 0;
    while n != 1 {
        if n % 2 == 0 { n = n // 2; } else { n = 3 * n + 1; }
        steps = steps + 1;
    }
    return steps;
}
let best = 1;
let best_len = 0;
let i = 1;
while i < 3000 {
    let l = chain_length(i);
    if l > best_len { best = i; best_len = l; }
    i = i + 1;
}
print("longest chain below 3000 starts at", best, "with", best_len, "steps");
