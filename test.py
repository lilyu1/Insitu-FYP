package application;

import javax.inject.Inject;
import javax.inject.Named;

import com.kuka.roboticsAPI.applicationModel.RoboticsAPIApplication;
import static com.kuka.roboticsAPI.motionModel.BasicMotions.*;

import com.kuka.roboticsAPI.conditionModel.ForceCondition;
import com.kuka.roboticsAPI.deviceModel.LBR;
import com.kuka.roboticsAPI.geometricModel.CartDOF;
import com.kuka.roboticsAPI.geometricModel.Frame;
import com.kuka.roboticsAPI.geometricModel.Tool;
import com.kuka.roboticsAPI.geometricModel.World;
import com.kuka.roboticsAPI.geometricModel.math.Vector;
import com.kuka.roboticsAPI.motionModel.IMotionContainer;
import com.kuka.roboticsAPI.motionModel.controlModeModel.CartesianImpedanceControlMode;
import com.kuka.roboticsAPI.sensorModel.ForceSensorData;
import com.kuka.task.ITaskLogger;
import com.kuka.common.ThreadUtil;
import com.kuka.generated.ioAccess.MediaFlangeIOGroup;

/**
 * Implementation of a robot application.
 * <p>
 * The application provides a {@link RoboticsAPITask#initialize()} and a 
 * {@link RoboticsAPITask#run()} method, which will be called successively in 
 * the application lifecycle. The application will terminate automatically after 
 * the {@link RoboticsAPITask#run()} method has finished or after stopping the 
 * task. The {@link RoboticsAPITask#dispose()} method will be called, even if an 
 * exception is thrown during initialization or run. 
 * <p>
 * <b>It is imperative to call <code>super.dispose()</code> when overriding the 
 * {@link RoboticsAPITask#dispose()} method.</b> 
 * 
 * @see UseRoboticsAPIContext
 * @see #initialize()
 * @see #run()
 * @see #dispose()
 */

public class Test3 extends RoboticsAPIApplication {
    @Inject
    private LBR robot;

    @Inject
    private MediaFlangeIOGroup mF;

    @Inject
    @Named("Electromagnet")
    private Tool EMagnet;

    @Inject
    private ITaskLogger logger;
    
    @Inject
	private OPCUA_Client_Control3 OPCUA;
    
    //corner of the printer bed
    private Frame f4;
    
    // Class-level variables for ForceConditions
    private ForceCondition touch;
    private ForceCondition touchB;

    // Initialise the application
    public void initialize() {
        EMagnet.attachTo(robot.getFlange());
        ThreadUtil.milliSleep(100);
        // Initialize the ForceConditions here
        touch = ForceCondition.createSpatialForceCondition(EMagnet.getFrame("/TCP"), 15, 20);
        touchB = ForceCondition.createSpatialForceCondition(EMagnet.getFrame("/TCP"), 15, 20);
        
        try {
			OPCUA.ServerUpdate();
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
    }

    private double[][] parseMagInfo(String magInfo) {
        // Remove the outer brackets and split the string by "],[" to get individual coordinate sets
        String cleanedMagInfo = magInfo.replace("[[", "").replace("]]", "");
        String[] coordinateSets = cleanedMagInfo.split("\\],\\[");

        // Initialize the array to hold the coordinates
        double[][] coordinates = new double[coordinateSets.length][3];

        // Loop through each coordinate set and split by commas to get x, y, z values
        for (int i = 0; i < coordinateSets.length; i++) {
            String[] xyz = coordinateSets[i].split(",");
            coordinates[i][0] = Double.parseDouble(xyz[0].trim());
            coordinates[i][1] = Double.parseDouble(xyz[1].trim());
            coordinates[i][2] = Double.parseDouble(xyz[2].trim());
        }

        return coordinates;
    }
    

    public void run() {
        //String magInfo = "[[123.0, 456.0, 0.6], [789.0, 657.0, 0.6]]";  // Example string
        //int magCount = 2;  // Example count
    	int magCount = OPCUA.magCount;
		String magInfo = OPCUA.magInfo;

    	//1. parse coordinates first
        double[][] coordinates = parseMagInfo(magInfo);
        logger.info("Magnet count: " + magCount);
        
        //2. calibrates to set f4 frame
        calibrateRobot();
        

        // 3. Loop through each magnet insertion
        for (int i = 0; i < magCount; i++) {
            double[] coord = coordinates[i];
            logger.info("Magnet info: " + coord[0] + ", " + coord[1] + ", " + coord[2]);
            //3a. go to f4
            EMagnet.move(ptp(f4).setJointVelocityRel(0.2)); //The printer (0,0)
            //3b. create new frame for each magnet
            Frame fMagnet = robot.getCurrentCartesianPosition(EMagnet.getFrame("/TCP"));
            
            //3c. Transform coordinates relative to the f4 frame
            int[] transformed = transform(
                (int) coord[0], (int) coord[1], (int) coord[2],
                (int) f4.getX(), (int) f4.getY(), (int) f4.getZ()
            );
            logger.info("transformed coord: " + transformed[0] + ", " + transformed[1] + ", " + transformed[2]);
            
            //3d. change frame coords to transformed coord
            fMagnet.setX(transformed[0]);
    		fMagnet.setY(transformed[1]);
    		fMagnet.setZ(transformed[2]);
            
            
            //3e. pickup magnet and goes to somewhere 
    		pickupMagnet(i);
    	
            //3f. insert magnet
            insertMagnetAtLocation(fMagnet);
        }
        
        
        //4. return to f4 then return to p22
        EMagnet.move(ptp(getApplicationData().getFrame("f4")).setJointVelocityRel(0.5));
        EMagnet.move(ptp(getApplicationData().getFrame("/P22")).setJointVelocityRel(0.5));
    }

    // Insert magnet at specified XYZ coordinates
    private void insertMagnetAtLocation(Frame fMagnet) {
        ForceCondition touch = ForceCondition.createSpatialForceCondition(EMagnet.getFrame("/TCP"), 15, 20);
        
        // Move to the specified XYZ coordinates
        EMagnet.move(ptp(fMagnet).setJointVelocityRel(0.2));

        // lower arm to insert
        IMotionContainer motion = EMagnet.move(linRel(0, 0, -80, World.Current.getRootFrame()).setCartVelocity(30).breakWhen(touch));
        if (motion.getFiredBreakConditionInfo() == null) {
            logger.info("No Collision Detected");
        } else {
            logger.info("Magnet inserted at " + fMagnet.getX() + ", " + fMagnet.getY() + ", " + fMagnet.getZ());
            mF.setLEDBlue(true);
            mF.setSwitchOffX3Voltage(false);  // Turn on magnet
            ThreadUtil.milliSleep(1500);
            mF.setLEDBlue(false);
            mF.setSwitchOffX3Voltage(true);   // Turn off magnet
        }

        // Move back up after insertion
        EMagnet.move(linRel(0, 0, 80, World.Current.getRootFrame()).setCartVelocity(30));
    }
    
    private void pickupMagnet(int magIdx) {
    	//Moving 5 up 
    	robot.move(linRel(0, 0, 5, World.Current.getRootFrame()).setCartVelocity(60));
    	//move above magnet 0 position
    	robot.move(linRel(45 - magIdx*30 , 120, 0, World.Current.getRootFrame()).setCartVelocity(60));
    	//Moving down to pick up magnet
		IMotionContainer motion3 = EMagnet.move(linRel(0, 0, -80, World.Current.getRootFrame()).setCartVelocity(30).breakWhen(touch));
		if (motion3.getFiredBreakConditionInfo() == null){
			logger.info("No Collision Detected");
		}
		else{
			logger.info("Picking up magnet");
			mF.setLEDBlue(true);
			mF.setSwitchOffX3Voltage(false);
			logger.info("Voltage on");
		}
    	
		//moving up
		robot.move(linRel(0, 0, 100, World.Current.getRootFrame()).setCartVelocity(60));
		//moving comfortably away from holder 
		robot.move(linRel(-30, -80, 0, World.Current.getRootFrame()).setCartVelocity(60));
    }
    
    
 // Calibration method
    private void calibrateRobot() {

        mF.setLEDBlue(false);
        mF.setSwitchOffX3Voltage(true);
        logger.info("Voltage off");

        EMagnet.move(ptp(getApplicationData().getFrame("/P22")).setJointVelocityRel(0.5));
        EMagnet.move(ptp(getApplicationData().getFrame("/P24")).setJointVelocityRel(0.5));

        Frame f0 = robot.getCurrentCartesianPosition(EMagnet.getFrame("/TCP"));
        Frame f1 = robot.getCurrentCartesianPosition(EMagnet.getFrame("/TCP"));
        Frame f2 = robot.getCurrentCartesianPosition(EMagnet.getFrame("/TCP"));
        Frame fP = robot.getCurrentCartesianPosition(EMagnet.getFrame("/TCP"));
        //Frame f3 = robot.getCurrentCartesianPosition(EMagnet.getFrame("/TCP"));
        Frame f4 = robot.getCurrentCartesianPosition(EMagnet.getFrame("/TCP"));
        //Frame f5 = robot.getCurrentCartesianPosition(EMagnet.getFrame("/TCP"));

        IMotionContainer motion1 = EMagnet.move(linRel(80, 0, 0, World.Current.getRootFrame()).setCartVelocity(5).breakWhen(touch));
        
        if (motion1.getFiredBreakConditionInfo() == null) {
            logger.info("No Collision Detected");
            EMagnet.move(lin(getApplicationData().getFrame("/P22")).setCartVelocity(50));
        } else {
            logger.info("Collision Detected");
            ThreadUtil.milliSleep(1000);    
            f0 = robot.getCurrentCartesianPosition(EMagnet.getFrame("/TCP"));
            EMagnet.move(linRel(-10, 0, 0, World.Current.getRootFrame()).setCartVelocity(40));
        }

        EMagnet.move(linRel(0, 0, 30, World.Current.getRootFrame()).setCartVelocity(50));
        EMagnet.move(linRel(40, 0, 0, World.Current.getRootFrame()).setCartVelocity(50));
        ThreadUtil.milliSleep(500);
        IMotionContainer motion0 = EMagnet.move(linRel(0, 0, -80, World.Current.getRootFrame()).setCartVelocity(5).breakWhen(touch));

        if (motion0.getFiredBreakConditionInfo() == null) {
            logger.info("No Collision Detected");
            EMagnet.move(lin(getApplicationData().getFrame("/P22")).setCartVelocity(50));
        } else {
            logger.info("Collision Detected");
            ThreadUtil.milliSleep(1000);    
            f1 = robot.getCurrentCartesianPosition(EMagnet.getFrame("/TCP"));
            EMagnet.move(linRel(0, 0, 10, World.Current.getRootFrame()).setCartVelocity(40));
        }

        EMagnet.move(linRel(0, 50, 0, World.Current.getRootFrame()).setCartVelocity(50));
        EMagnet.move(linRel(0, 0, -30, World.Current.getRootFrame()).setCartVelocity(40));
        ThreadUtil.milliSleep(1000);
        IMotionContainer motion2 = EMagnet.move(linRel(0, -100, 0, World.Current.getRootFrame()).setCartVelocity(5).breakWhen(touchB));

        if (motion2.getFiredBreakConditionInfo() == null) {
            logger.info("No Collision Detected");
            EMagnet.move(lin(getApplicationData().getFrame("/P22")).setCartVelocity(50));
        } else {
            ThreadUtil.milliSleep(1000);    
            logger.info("Collision Detected");
            f2 = robot.getCurrentCartesianPosition(EMagnet.getFrame("/TCP"));
            EMagnet.move(linRel(0, 10, 0, World.Current.getRootFrame()).setCartVelocity(40));
            EMagnet.move(linRel(-200, 0, 0, World.Current.getRootFrame()).setCartVelocity(60));
        }

        fP.setX(f0.getX()); 
        fP.setZ(f1.getZ());
        fP.setY(f2.getY());

        f4.setX(fP.getX() - 216);
        f4.setZ(fP.getZ() - 372);
        f4.setY(fP.getY() - 91);
        
        logger.info("Calibration complete");
        
    }
    
    public static int[] transform(int x, int y, int z, int fx, int fy, int fz) {
        x = fx + x ; 
        y = fy - y;  
        z = fz + z;  

        return new int[]{x, y, z};
}
}

