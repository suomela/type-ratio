#include <algorithm>
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <system_error>
#include <unordered_set>
#include <vector>

namespace type_ratio {

namespace fs = std::filesystem;
using std::ifstream;
using std::ofstream;
using std::pair;
using std::string;
using std::vector;
using ll = long long;
using rng_t = std::mt19937_64;
using flag_t = int;

constexpr ll exact_preference = 10;
const fs::path data_dir = "type-ratio-data";
const fs::path dir_in = fs::path(data_dir) / "in";
const fs::path dir_out = fs::path(data_dir) / "out";

class Work {
  public:
    explicit Work(string fn_, ll iter_) : fn{fn_}, iter{iter_} {}

    void run() {
        read_data();
        msg("+");
        calc();
        msg("-");
        write_data();
    }

    void read_data() {
        fs::path input = dir_in / fn;
        try {
            ifstream f(input);
            f.exceptions(ifstream::failbit | ifstream::badbit);
            f >> n >> m0 >> m1;
            mm = m0 + m1;
            data.resize(n);
            for (int i = 0; i < n; ++i) {
                read_into(f, data[i], m0, 0);
                read_into(f, data[i], m1, m0);
            }
        } catch (const std::ios_base::failure &e) {
            throw std::ios_base::failure(input, e.code());
        }
    }

    void write_data() {
        string fn2 = fn;
        if (!small) {
            fn2 += "." + std::to_string(iter);
        }
        fs::path output = dir_out / fn2;
        try {
            ofstream f(output);
            f.exceptions(ofstream::failbit | ofstream::badbit);
            for (int x = 0; x < mm + 1; ++x) {
                pair<int, int> r = acc_range(x);
                f << r.first << " " << r.second;
                for (int y = r.first; y < r.second; ++y) {
                    f << " " << get_acc(x, y);
                }
                f << "\n";
            }
        } catch (const std::ios_base::failure &e) {
            throw std::ios_base::failure(output, e.code());
        }
    }

    void calc() {
        init_calc();
        check_size();
        if (small) {
            calc_exact();
        } else {
            calc_random();
        }
    }

  private:
    void msg(string m) {
#pragma omp critical
        {
            std::cout << m << " " << fn << "  " << n << " " << m0 << "+" << m1
                      << std::endl;
        }
    }

    static void read_into(ifstream &f, vector<int> &v, int range, int base) {
        while (true) {
            int a;
            f >> a;
            if (a == -1) {
                break;
            }
            assert(0 <= a && a < range);
            v.push_back(a + base);
        }
    }

    void init_calc() {
        order.resize(n);
        accum.resize((m0 + 1) * (mm + 1));
        seen.resize(mm);
        for (int j = 0; j < n; ++j) {
            order[j] = j;
        }
        for (int x = 0; x < mm + 1; ++x) {
            for (int y = 0; y < m0 + 1; ++y) {
                clear_acc(x, y);
            }
        }
    }

    void check_size() {
        small = false;
        ll perm = 1;
        for (int i = 0; i < n; ++i) {
            perm *= (i + 1);
            if (perm > exact_preference * iter) {
                return;
            }
        }
        small = true;
    }

    void calc_random() {
        rng.seed(1);
        for (ll it = 0; it < iter; ++it) {
            shuffle(begin(order), end(order), rng);
            process_order();
        }
    }

    void calc_exact() {
        do {
            process_order();
        } while (std::next_permutation(begin(order), end(order)));
    }

    inline void process_order() {
        for (int i = 0; i < mm; ++i) {
            seen[i] = 0;
        }
        int x = 0;
        int y = 0;
        for (int j = 0; j < n; ++j) {
            const vector<int> &vec = data[order[j]];
            for (int v : vec) {
                if (!seen[v]) {
                    seen[v] = 1;
                    ++x;
                    if (v < m0) {
                        ++y;
                    }
                }
            }
            inc_acc(x, y);
        }
    }

    inline ll get_acc(int x, int y) const { return accum[x * (m0 + 1) + y]; }

    inline pair<int, int> acc_range(int x) const {
        int first = 0;
        while (first < m0 + 1 && get_acc(x, first) == 0) {
            ++first;
        }
        int last = m0 + 1;
        while (last > first && get_acc(x, last - 1) == 0) {
            --last;
        }
        if (first == last) {
            first = last = 0;
        }
        return std::make_pair(first, last);
    }

    inline void inc_acc(int x, int y) { ++accum[x * (m0 + 1) + y]; }

    inline void clear_acc(int x, int y) { accum[x * (m0 + 1) + y] = 0; }

    const string fn;
    const ll iter;
    int n;
    int mm;
    int m0;
    int m1;
    bool small;
    vector<vector<int>> data;
    vector<int> order;
    vector<ll> accum;
    vector<flag_t> seen;
    rng_t rng;
};

class Driver {
  public:
    explicit Driver(ll iter_, int mypart_, int parts_) : iter{iter_}, mypart{mypart_}, parts{parts_} {}

    void run() {
        get_work();
        do_work();
    }

    void get_work() {
        std::unordered_set<string> work_set;
        for (const auto &p : fs::directory_iterator(dir_in)) {
            string fn = p.path().filename();
            auto dot = fn.find('.');
            if (dot == string::npos) {
                work_set.insert(fn);
            } else if (dot > 0) {
                std::cerr << "unexpected file name: " << p.path() << std::endl;
            }
        }
        fs::create_directories(dir_out);
        for (const auto &p : fs::directory_iterator(dir_out)) {
            string fn2 = p.path().filename();
            auto dot = fn2.find('.');
            if (dot == string::npos) {
                work_set.erase(fn2);
            } else if (dot > 0) {
                string fn = fn2.substr(0, dot);
                string ext = fn2.substr(dot + 1);
                try {
                    ll has_it = std::stoll(ext);
                    if (has_it >= iter) {
                        work_set.erase(fn);
                    }
                } catch (const std::logic_error &e) {
                    std::cerr << "unexpected file name: " << p.path() << std::endl;
                }
            }
        }
        vector<string> todo(begin(work_set), end(work_set));
        std::sort(begin(todo), end(todo));
        work.reserve(todo.size());
        for (const auto &s : todo) {
            work.emplace_back(s, iter);
        }
    }

    void do_work() {
        int n = work.size();
#pragma omp parallel for schedule(dynamic)
        for (int i = 0; i < n; ++i) {
            work[i].run();
        }
    }

  private:
    const ll iter;
    const int mypart;
    const int parts;
    vector<Work> work;
};

} // namespace type_ratio

int main(int argc, const char **argv) {
    if (argc != 2 && argc != 4) {
        std::cerr << "usage: " << argv[0] << " ITER [PART-NUMBER NUMBER-OF-PARTS]" << std::endl;
        std::exit(1);
    }

    long long iter;
    int mypart = 0;
    int parts = 1;
    try {
        iter = std::stoll(argv[1]);
        if (argc == 4) {
            mypart = std::stoi(argv[2]);
            parts = std::stoi(argv[3]);
        }
    } catch (const std::logic_error &e) {
        std::cerr << "invalid argument" << std::endl;
        std::exit(1);
    }
    if (mypart == parts) {
        // Can specify parts 0/4 ... 3/4 or 1/4 ... 4/4
        mypart = 0;
    }
    if (!(0 <= iter && 0 <= mypart && mypart < parts)) {
        std::cerr << "invalid argument" << std::endl;
        std::exit(1);
    }

    try {
        type_ratio::Driver d(iter, mypart, parts);
        d.run();
    } catch (const std::system_error &e) {
        std::cerr << e.what() << std::endl;
        std::exit(1);
    }
}
