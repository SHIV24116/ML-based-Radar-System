import schemdraw
import schemdraw.elements as elm

with schemdraw.Drawing() as d:

    # Radar source
    d += elm.SourceV().label('CDM324\nRadar OUT', loc='left')

    # High-pass filter
    d += elm.Capacitor().right().label('C1\n0.22uF')
    d += elm.Dot().label('Node A')

    # R1 to ground (HPF)
    d.push()
    d += elm.Resistor().down().label('R1\n100k')
    d += elm.Ground()
    d.pop()

    # Op-amp
    op = d.add(elm.Opamp().right().label('MCP6002'))

    # Connect Node A to IN+
    d += elm.Line().at((d.here[0]-2, d.here[1])).to(op.in1)

    # Gain network (corrected)
    # IN- node
    d += elm.Line().at(op.in2).left().length(1)
    d += elm.Dot()

    # R2 from IN- to GND
    d.push()
    d += elm.Resistor().down().label('R2\n10k')
    d += elm.Ground()
    d.pop()

    # Feedback R3 from OUT to IN-
    d += elm.Resistor().at(op.out).to(op.in2).label('R3\n100k')

    # Output line
    d += elm.Line().at(op.out).right()

    # Low-pass filter
    d += elm.Resistor().right().label('R4\n3.3k')
    d += elm.Dot().label('Node B')

    # Capacitor to ground
    d.push()
    d += elm.Capacitor().down().label('C2\n0.1uF')
    d += elm.Ground()
    d.pop()

    # ADC output
    d += elm.Line().right().label('ESP32 ADC')

    # Save file
    d.save(r'C:\Users\RUPENDRA SINGH\Desktop\PR project\correct_radar_circuit.png')