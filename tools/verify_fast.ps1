$code = @"
using System;
using System.IO;

public class VerifyPac {
    private static ushort[] table = new ushort[256];
    static VerifyPac() {
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

    public static void Verify(string pacPath) {
        byte[] pac = File.ReadAllBytes(pacPath);
        uint magic = BitConverter.ToUInt32(pac, 2116);
        ushort crc1Stored = BitConverter.ToUInt16(pac, 2120);
        ushort crc2Stored = BitConverter.ToUInt16(pac, 2122);

        ushort crc1Calc = Crc16Arc(pac, 0, 2120);
        ushort crc2Calc = Crc16Arc(pac, 2124, pac.Length - 2124);

        Console.WriteLine("File: " + pacPath + " (" + pac.Length + " bytes)");
        Console.WriteLine("Magic: 0x" + magic.ToString("X8") + (magic == 0xFFFAFFFA ? " (OK)" : " (INVALID)"));
        Console.WriteLine("CRC1: stored 0x" + crc1Stored.ToString("X4") + ", calc 0x" + crc1Calc.ToString("X4") + (crc1Stored == crc1Calc ? " (OK)" : " (BAD)"));
        Console.WriteLine("CRC2: stored 0x" + crc2Stored.ToString("X4") + ", calc 0x" + crc2Calc.ToString("X4") + (crc2Stored == crc2Calc ? " (OK)" : " (BAD)"));

        // Verify the corrupted bytes
        int sigStart = 1084024 + 12230884 - 256;
        bool corruptOk = true;
        for (int i = 0; i < 256; i++) {
            byte expected = (byte)(i % 4 == 0 ? 0xDE : i % 4 == 1 ? 0xAD : i % 4 == 2 ? 0xBE : 0xEF);
            if (pac[sigStart + i] != expected) {
                corruptOk = false;
                break;
            }
        }
        Console.WriteLine("Signature trailer corrupt check: " + (corruptOk ? "CORRUPTED (DEADBEEF verified)" : "FAILED"));
    }
}
"@

Add-Type -TypeDefinition $code
[VerifyPac]::Verify("3210_signature_test.pac")
