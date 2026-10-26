$code = @"
using System;
using System.IO;

public class PacPatcher {
    private static ushort[] table = new ushort[256];
    static PacPatcher() {
        for (int i = 0; i < 256; i++) {
            ushort c = (ushort)i;
            for (int j = 0; j < 8; j++) {
                c = (c & 1) != 0 ? (ushort)((c >> 1) ^ 0xA001) : (ushort)(c >> 1);
            }
            table[i] = c;
        }
    }

    public static ushort Crc16Arc(byte[] data, int offset, int length) {
        ushort crc = 0;
        for (int i = offset; i < offset + length; i++) {
            crc = (ushort)((crc >> 8) ^ table[(crc ^ data[i]) & 0xFF]);
        }
        return crc;
    }

    public static void PatchSignature(string inputPac, string outputPac) {
        Console.WriteLine("Reading " + inputPac + "...");
        byte[] pac = File.ReadAllBytes(inputPac);

        // Partition 5: UserImg
        // Offset: 1,084,024, Size: 12,230,884
        int userImgOffset = 1084024;
        int userImgSize = 12230884;
        int sigStart = userImgOffset + userImgSize - 256;

        Console.WriteLine("Corrupting RSA signature trailer at offset " + sigStart + " (256 bytes)...");
        byte[] deadbeef = new byte[] { 0xDE, 0xAD, 0xBE, 0xEF };
        for (int i = 0; i < 256; i++) {
            pac[sigStart + i] = deadbeef[i % 4];
        }

        Console.WriteLine("Recomputing CRC2 (bytes [2124..EOF])...");
        ushort crc2 = Crc16Arc(pac, 2124, pac.Length - 2124);
        Console.WriteLine("New CRC2: 0x" + crc2.ToString("X4"));

        // Store crc2 at offset 2122 (little-endian u16)
        pac[2122] = (byte)(crc2 & 0xFF);
        pac[2123] = (byte)((crc2 >> 8) & 0xFF);

        // Note: CRC1 is over [0..2120), which is untouched!
        Console.WriteLine("Writing " + outputPac + "...");
        File.WriteAllBytes(outputPac, pac);
        Console.WriteLine("SUCCESS! Generated " + outputPac + " (" + pac.Length + " bytes)");
    }
}
"@

Add-Type -TypeDefinition $code
$sw = [System.Diagnostics.Stopwatch]::StartNew()
[PacPatcher]::PatchSignature("3210.pac", "3210_signature_test.pac")
$sw.Stop()
Write-Host "Completed in $($sw.ElapsedMilliseconds) ms"
