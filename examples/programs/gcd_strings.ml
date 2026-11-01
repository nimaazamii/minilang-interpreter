fn gcd(a, b) {
    while b != 0 {
        let t = b;
        b = a % b;
        a = t;
    }
    return a;
}
print("gcd(1071, 462) =", gcd(1071, 462));
let greeting = "Hello, " + "MiniLang";
print(greeting, "has", len(greeting), "characters");
print(10 / 4, 10 // 4, 10 % 4, -7 // 2, 2.5 * 2);
