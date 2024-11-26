#include <iostream>
#include <vector>
#include <algorithm>

#define IMAGE_SIZE 128
#define KERNEL_SIZE 3
#define TILE_SIZE 8

void tiled_convolution(const std::vector<std::vector<int>>& image, 
                       const std::vector<std::vector<int>>& kernel, 
                       std::vector<std::vector<int>>& output) {
    int pad = KERNEL_SIZE / 2;

    // Iterate over tiles
    for (int i = 0; i < IMAGE_SIZE; i += TILE_SIZE) {
        for (int j = 0; j < IMAGE_SIZE; j += TILE_SIZE) {
            // Process each tile
            for (int ii = i; ii < std::min(i + TILE_SIZE, IMAGE_SIZE); ii++) {
                for (int jj = j; jj < std::min(j + TILE_SIZE, IMAGE_SIZE); jj++) {
                    int sum = 0;

                    // Apply kernel
                    for (int ki = -pad; ki <= pad; ki++) {
                        for (int kj = -pad; kj <= pad; kj++) {
                            int ni = ii + ki; // Neighbor row
                            int nj = jj + kj; // Neighbor column

                            // Check boundary conditions
                            if (ni >= 0 && ni < IMAGE_SIZE && nj >= 0 && nj < IMAGE_SIZE) {
                                sum += image[ni][nj] * kernel[pad + ki][pad + kj];
                            }
                        }
                    }

                    output[ii][jj] = sum;
                }
            }
        }
    }
}

int main() {
    // Initialize image and kernel
    std::vector<std::vector<int>> image(IMAGE_SIZE, std::vector<int>(IMAGE_SIZE, 1)); // Example: All pixels are 1
    std::vector<std::vector<int>> kernel = { {0, -1, 0},
                                             {-1, 5, -1},
                                             {0, -1, 0} }; // Example: Sharpen filter
    std::vector<std::vector<int>> output(IMAGE_SIZE, std::vector<int>(IMAGE_SIZE, 0));

    tiled_convolution(image, kernel, output);

    std::cout << "Convolution completed!" << std::endl;

    return 0;
}
