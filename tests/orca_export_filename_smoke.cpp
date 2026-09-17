// Standalone test of the exact C++ filename helper used by the local Orca build.
#include "ExportFilename.hpp"
#include <cassert>
#include <iostream>

int main()
{
    using Slic3r::GUI::export_file_stem;
    assert(export_file_stem("_local/profilelab_123/Workshop MK3S") == "Workshop MK3S");
    assert(export_file_stem("_subscribed/vendor_123/Workshop MK3S") == "Workshop MK3S");
    assert(export_file_stem("Ordinary Printer 0.4 nozzle") == "Ordinary Printer 0.4 nozzle");
    assert(export_file_stem("_local/id/Printer: A/B\\C") == "Printer_ A_B_C");
    assert(export_file_stem("CON") == "_CON");
    assert(export_file_stem("lpt1.json") == "_lpt1.json");
    assert(export_file_stem("...") == "Profile");
    assert(export_file_stem("Printer. ") == "Printer");
    std::cout << "8 filename cases passed\n";
}
