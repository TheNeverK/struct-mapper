struct simple {
    int (*fun)(int);
};

struct simple1 {
    int a;
    char c;
};

struct simple2 {
    char* str, ch;
    int *const *npp;
    short int s;
    int arr[3];
    struct simple1 nested;
    int (*fun)(int);
    struct {
        float x;
        float y;
    } point;
};
