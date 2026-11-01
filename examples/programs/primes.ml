# counts the primes below 1000 by trial division
fn is_prime(n) {
    if n < 2 { return false; }
    let d = 2;
    while d * d <= n {
        if n % d == 0 { return false; }
        d = d + 1;
    }
    return true;
}
let count = 0;
let n = 2;
while n < 1000 {
    if is_prime(n) { count = count + 1; }
    n = n + 1;
}
print("primes below 1000:", count);
